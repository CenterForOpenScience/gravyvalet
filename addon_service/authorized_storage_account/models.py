from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from django.core.exceptions import ValidationError
from django.db import (
    models,
    transaction,
)

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.common.validators import validate_addon_capability
from addon_service.credentials.models import ExternalCredentials
from addon_service.oauth import utils as oauth_utils
from addon_service.oauth.models import (
    OAuth2ClientConfig,
    OAuth2TokenMetadata,
)
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
)
from addon_toolkit.interfaces.storage import StorageConfig


class AuthorizedStorageAccountManager(models.Manager):

    def active(self):
        """filter to accounts owned by non-deactivated users"""
        return self.get_queryset().filter(account_owner__deactivated__isnull=True)


class AuthorizedStorageAccount(AddonsServiceBaseModel):
    """Model for descirbing a user's account on an ExternalStorageService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    objects = AuthorizedStorageAccountManager()

    _display_name = models.CharField(null=False, blank=True, default="")
    external_account_id = models.CharField(null=False, blank=True, default="")
    int_authorized_capabilities = models.IntegerField(
        validators=[validate_addon_capability]
    )
    default_root_folder = models.CharField(blank=True)
    _api_base_url = models.URLField(blank=True)

    external_storage_service = models.ForeignKey(
        "addon_service.ExternalStorageService",
        on_delete=models.CASCADE,
        related_name="authorized_storage_accounts",
    )
    account_owner = models.ForeignKey(
        "addon_service.UserReference",
        on_delete=models.CASCADE,
        related_name="authorized_storage_accounts",
    )
    _credentials = models.OneToOneField(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        primary_key=False,
        null=True,
        blank=True,
        related_name="authorized_storage_account",
    )
    oauth2_token_metadata = models.ForeignKey(
        "addon_service.OAuth2TokenMetadata",
        on_delete=models.CASCADE,  # probs not
        null=True,
        blank=True,
        related_name="authorized_storage_accounts",
    )

    class Meta:
        verbose_name = "Authorized Storage Account"
        verbose_name_plural = "Authorized Storage Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-storage-accounts"

    @property
    def display_name(self):
        return self._display_name or self.external_service.display_name

    @display_name.setter
    def display_name(self, value: str):
        self._display_name = value

    @property
    def external_service(self):
        return self.external_storage_service

    @property
    def credentials_format(self):
        return self.external_service.credentials_format

    @property
    def credentials(self):
        if self._credentials:
            return self._credentials.decrypted_credentials
        return None

    @credentials.setter
    def credentials(self, credentials_data):
        creds_type = type(credentials_data)
        if creds_type is not self.credentials_format.dataclass:
            raise ValidationError(
                f"Expectd credentials of type type {self.credentials_format.dataclass}."
                f"Got credentials of type {creds_type}."
            )
        if not self._credentials:
            self._credentials = ExternalCredentials.new()
        try:
            self._credentials.decrypted_credentials = credentials_data
            self._credentials.save()
        except TypeError as e:
            raise ValidationError(e)

    @property
    def authorized_capabilities(self) -> AddonCapabilities:
        """get the enum representation of int_authorized_capabilities"""
        return AddonCapabilities(self.int_authorized_capabilities)

    @authorized_capabilities.setter
    def authorized_capabilities(self, new_capabilities: AddonCapabilities):
        """set int_authorized_capabilities without caring it's int"""
        self.int_authorized_capabilities = new_capabilities.value

    @property
    def owner_uri(self) -> str:
        """Convenience property to simplify permissions checking."""
        return self.account_owner.user_uri

    @property
    def authorized_operations(self) -> list[AddonOperationModel]:
        _imp_cls = self.imp_cls
        return [
            AddonOperationModel(_imp_cls, _operation)
            for _operation in _imp_cls.implemented_operations_for_capabilities(
                self.authorized_capabilities
            )
        ]

    @property
    def authorized_operation_names(self) -> list[str]:
        return [
            _operation.name
            for _operation in self.imp_cls.implemented_operations_for_capabilities(
                self.authorized_capabilities
            )
        ]

    @property
    def auth_url(self) -> str | None:
        """Generates the url required to initiate OAuth2 credentials exchange.

        Returns None if the ExternalStorageService does not support OAuth2
        or if the initial credentials exchange has already ocurred.
        """
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            return None

        state_token = self.oauth2_token_metadata.state_token
        if not state_token:
            return None
        return oauth_utils.build_auth_url(
            auth_uri=self.external_service.oauth2_client_config.auth_uri,
            client_id=self.external_service.oauth2_client_config.client_id,
            state_token=state_token,
            authorized_scopes=self.oauth2_token_metadata.authorized_scopes,
            redirect_uri=self.external_service.oauth2_client_config.auth_callback_url,
        )

    @property
    def api_base_url(self):
        return self._api_base_url or self.external_service.api_base_url

    @api_base_url.setter
    def api_base_url(self, value):
        self._api_base_url = value

    @property
    def imp_cls(self) -> type[AddonImp]:
        return self.external_service.addon_imp.imp_cls

    @property
    def credentials_available(self) -> bool:
        return self._credentials is not None

    @transaction.atomic
    def initiate_oauth2_flow(self, authorized_scopes=None):
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            raise ValueError("Cannot initaite OAuth flow for non-OAuth credentials")
        self.oauth2_token_metadata = OAuth2TokenMetadata.objects.create(
            authorized_scopes=(
                authorized_scopes or self.external_service.supported_scopes
            ),
            state_nonce=oauth_utils.generate_state_nonce(),
        )
        self.save()

    def storage_imp_config(self) -> StorageConfig:
        return StorageConfig(
            max_upload_mb=self.external_service.max_upload_mb,
            external_api_url=self.api_base_url,
            connected_root_id=self.default_root_folder,
            external_account_id=self.external_account_id,
        )

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        self.validate_api_base_url()
        self.validate_oauth_state()

    def validate_api_base_url(self):
        service = self.external_service
        if self._api_base_url and not service.configurable_api_root:
            raise ValidationError(
                {
                    "api_base_url": f"Cannot specify an api_base_url for Public-only service {service.display_name}"
                }
            )
        if ServiceTypes.PUBLIC not in service.service_type and not self.api_base_url:
            raise ValidationError(
                {
                    "api_base_url": f"Must specify an api_base_url for Hosted-only service {service.display_name}"
                }
            )

    def validate_oauth_state(self):
        if (
            self.credentials_format is not CredentialsFormats.OAUTH2
            or not self.oauth2_token_metadata
        ):
            return
        if bool(self.credentials) == bool(self.oauth2_token_metadata.state_nonce):
            raise ValidationError(
                {
                    "credentials": "OAuth2 accounts must assign exactly one of state_nonce and access_token"
                }
            )
        if self.credentials and not self.oauth2_token_metadata.refresh_token:
            raise ValidationError(
                {
                    "credentials": "OAuth2 accounts with an access token must have a refresh token"
                }
            )

    ###
    # async functions for use in oauth callback flows

    async def refresh_oauth_access_token(self) -> None:
        _oauth_client_config, _oauth_token_metadata = (
            await self._load_client_config_and_token_metadata()
        )
        _fresh_token_result = await oauth_utils.get_refreshed_access_token(
            token_endpoint_url=_oauth_client_config.token_endpoint_url,
            refresh_token=_oauth_token_metadata.refresh_token,
            auth_callback_url=_oauth_client_config.auth_callback_url,
            client_id=_oauth_client_config.client_id,
            client_secret=_oauth_client_config.client_secret,
        )
        await _oauth_token_metadata.update_with_fresh_token(_fresh_token_result)
        await sync_to_async(self.refresh_from_db)()

    refresh_oauth_access_token__blocking = async_to_sync(refresh_oauth_access_token)

    @sync_to_async
    def _load_client_config_and_token_metadata(
        self,
    ) -> tuple[OAuth2ClientConfig, OAuth2TokenMetadata]:
        # wrap db access in `sync_to_async`
        return (
            self.external_service.oauth2_client_config,
            self.oauth2_token_metadata,
        )
