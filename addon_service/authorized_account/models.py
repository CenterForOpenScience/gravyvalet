from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from django.core.exceptions import ValidationError
from django.db import (
    models,
    transaction,
)

from addon_service.addon_imp.instantiation import get_addon_instance
from addon_service.addon_operation.models import AddonOperationModel
from addon_service.authorized_account.utils import get_config_for_account
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.common.validators import validate_addon_capability
from addon_service.credentials.models import ExternalCredentials
from addon_service.oauth1 import utils as oauth1_utils
from addon_service.oauth2 import utils as oauth2_utils
from addon_service.oauth2.models import (
    OAuth2ClientConfig,
    OAuth2TokenMetadata,
)
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
)
from addon_toolkit.credentials import (
    Credentials,
    OAuth1Credentials,
)


class AuthorizedAccountManager(models.Manager):
    def active(self):
        """filter to accounts owned by non-deactivated users"""
        return self.get_queryset().filter(account_owner__deactivated__isnull=True)


class AuthorizedAccount(AddonsServiceBaseModel):
    """Model for describing a user's account on an ExternalService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    account_owner = models.ForeignKey(
        "addon_service.UserReference",
        on_delete=models.CASCADE,
        related_name="authorized_accounts",
    )
    _credentials = models.OneToOneField(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        primary_key=False,
        null=True,
        blank=True,
        related_name="authorized_account",
    )
    _temporary_oauth1_credentials = models.OneToOneField(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        primary_key=False,
        null=True,
        blank=True,
        related_name="temporary_authorized_account",
    )
    oauth2_token_metadata = models.ForeignKey(
        "addon_service.OAuth2TokenMetadata",
        on_delete=models.CASCADE,  # probs not
        null=True,
        blank=True,
        related_name="authorized_accounts",
    )

    objects = AuthorizedAccountManager()
    external_service = models.ForeignKey(
        "addon_service.ExternalService", on_delete=models.CASCADE
    )
    _display_name = models.CharField(null=False, blank=True, default="")
    external_account_id = models.CharField(null=False, blank=True, default="")
    int_authorized_capabilities = models.IntegerField(
        validators=[validate_addon_capability]
    )
    _api_base_url = models.URLField(blank=True)

    @property
    def display_name(self):
        return self._display_name or self.external_service.display_name

    @display_name.setter
    def display_name(self, value: str):
        value = value if value is not None else ""
        self._display_name = value

    @property
    def credentials_format(self):
        return self.external_service.credentials_format

    @property
    def credentials(self):
        if self._credentials:
            return self._credentials.decrypted_credentials
        return None

    @credentials.setter
    def credentials(self, credentials_data: Credentials) -> None:
        if self.temporary_oauth1_credentials:
            self._temporary_oauth1_credentials.delete()
            self._temporary_oauth1_credentials = None
        self._set_credentials("_credentials", credentials_data)

    @property
    def temporary_oauth1_credentials(self) -> OAuth1Credentials | None:
        if self._temporary_oauth1_credentials:
            return self._temporary_oauth1_credentials.decrypted_credentials
        return None

    @temporary_oauth1_credentials.setter
    def temporary_oauth1_credentials(self, credentials_data: OAuth1Credentials) -> None:
        if self.credentials_format is not CredentialsFormats.OAUTH1A:
            raise ValidationError(
                "Trying to set temporary credentials for non OAuth1A account"
            )
        self._set_credentials("_temporary_oauth1_credentials", credentials_data)

    def _set_credentials(self, credentials_field: str, credentials_data: Credentials):
        creds_type = type(credentials_data)
        if not hasattr(self, credentials_field):
            raise ValidationError("Trying to set credentials to non-existing field")
        if creds_type is not self.credentials_format.dataclass:
            raise ValidationError(
                f"Expected credentials of type {self.credentials_format.dataclass}."
                f"Got credentials of type {creds_type}."
            )
        if not getattr(self, credentials_field, None):
            setattr(self, credentials_field, ExternalCredentials.new())
        try:
            creds = getattr(self, credentials_field)
            creds.decrypted_credentials = credentials_data
            creds.save()
        except TypeError as e:
            raise ValidationError(e)

    @property
    def authorized_capabilities(self) -> AddonCapabilities:
        """get the enum representation of int_authorized_capabilities"""
        return AddonCapabilities(self.int_authorized_capabilities)

    @authorized_capabilities.setter
    def authorized_capabilities(self, new_capabilities: AddonCapabilities):
        """set int_authorized_capabilities without caring its int"""
        self.int_authorized_capabilities = new_capabilities.value

    @property
    def owner_uri(self) -> str:
        """Convenience property to simplify permissions checking."""
        return self.account_owner.user_uri

    @property
    def authorized_operations(self) -> list[AddonOperationModel]:
        _imp_cls = self.imp_cls
        return [
            AddonOperationModel(_imp_cls.ADDON_INTERFACE, _operation)
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
        """Generates the url required to initiate OAuth credentials exchange.

        Returns None if the ExternalStorageService does not support OAuth
        or if the initial credentials exchange has already occurred.
        """
        match self.credentials_format:
            case CredentialsFormats.OAUTH2:
                return self.oauth2_auth_url
            case CredentialsFormats.OAUTH1A:
                return self.oauth1_auth_url
        return None

    @property
    def oauth1_auth_url(self) -> str | None:
        client_config = self.external_service.oauth1_client_config
        if client_config and self._temporary_oauth1_credentials:
            return oauth1_utils.build_auth_url(
                auth_uri=client_config.auth_url,
                temporary_oauth_token=self._temporary_oauth1_credentials.decrypted_credentials.oauth_token,
            )
        return None

    @property
    def oauth2_auth_url(self) -> str | None:
        _token_metadata = self.oauth2_token_metadata
        if not _token_metadata or not _token_metadata.state_token:
            return None
        return oauth2_utils.build_auth_url(
            auth_uri=self.external_service.oauth2_client_config.auth_uri,
            client_id=self.external_service.oauth2_client_config.client_id,
            state_token=_token_metadata.state_token,
            authorized_scopes=self.oauth2_token_metadata.authorized_scopes,
            redirect_uri=self.external_service.oauth2_client_config.auth_callback_url,
        )

    @property
    def api_base_url(self) -> str:
        return self._api_base_url or self.external_service.api_base_url

    @api_base_url.setter
    def api_base_url(self, value: str):
        self._api_base_url = (
            "" if (value == self.external_service.api_base_url or not value) else value
        )

    @property
    def imp_cls(self) -> type[AddonImp]:
        return self.external_service.addon_imp.imp_cls

    @property
    def credentials_available(self) -> bool:
        return self._credentials is not None

    @transaction.atomic
    def initiate_oauth1_flow(self):
        if self.credentials_format is not CredentialsFormats.OAUTH1A:
            raise ValueError("Cannot initiate OAuth1 flow for non-OAuth1 credentials")
        client_config = self.external_service.oauth1_client_config
        request_token_result, _ = async_to_sync(oauth1_utils.get_temporary_token)(
            client_config.request_token_url,
            client_config.client_key,
            client_config.client_secret,
        )
        self.temporary_oauth1_credentials = request_token_result
        self.save()

    @transaction.atomic
    def initiate_oauth2_flow(self, authorized_scopes=None):
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            raise ValueError("Cannot initiate OAuth2 flow for non-OAuth2 credentials")
        self.oauth2_token_metadata = OAuth2TokenMetadata.objects.create(
            authorized_scopes=(
                authorized_scopes or self.external_service.supported_scopes
            ),
            state_nonce=oauth2_utils.generate_state_nonce(),
        )
        self.save()

    def clean(self):
        super().clean()
        self.validate_api_base_url()
        self.validate_oauth_state()

    def validate_api_base_url(self) -> None:
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

    def validate_oauth_state(self) -> None:
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

    async def execute_post_auth_hook(self, auth_extras: dict | None = None):
        imp = await get_addon_instance(
            self.imp_cls, self, await sync_to_async(get_config_for_account)(self)
        )
        self.external_account_id = await imp.get_external_account_id(auth_extras or {})
        await self.asave()

    ###
    # async functions for use in oauth2 callback flows

    async def refresh_oauth2_access_token(self) -> None:
        (
            _oauth_client_config,
            _oauth_token_metadata,
        ) = await self._load_oauth2_client_config_and_token_metadata()
        _fresh_token_result = await oauth2_utils.get_refreshed_access_token(
            token_endpoint_url=_oauth_client_config.token_endpoint_url,
            refresh_token=_oauth_token_metadata.refresh_token,
            auth_callback_url=_oauth_client_config.auth_callback_url,
            client_id=_oauth_client_config.client_id,
            client_secret=_oauth_client_config.client_secret,
        )
        await _oauth_token_metadata.update_with_fresh_token(_fresh_token_result)
        await self.arefresh_from_db()

    refresh_oauth_access_token__blocking = async_to_sync(refresh_oauth2_access_token)

    @sync_to_async
    def _load_oauth2_client_config_and_token_metadata(
        self,
    ) -> tuple[OAuth2ClientConfig, OAuth2TokenMetadata]:
        # wrap db access in `sync_to_async`
        return (
            self.external_service.oauth2_client_config,
            self.oauth2_token_metadata,
        )

    @sync_to_async
    def get_credentials__async(self):
        if self._credentials:
            return self._credentials.decrypted_credentials
        return None
