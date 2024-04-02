from typing import Iterator

from django.core.exceptions import ValidationError
from django.db import (
    models,
    transaction,
)

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_addon_capability
from addon_service.credentials import (
    CredentialsFormats,
    ExternalCredentials,
)
from addon_service.oauth.models import OAuth2TokenMetadata
from addon_service.oauth.utils import (
    build_auth_url,
    generate_state_nonce,
)
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    AddonOperationImp,
)

from .validators import (
    validate_api_base_url,
    validate_oauth_state,
)


class AuthorizedStorageAccount(AddonsServiceBaseModel):
    """Model for descirbing a user's account on an ExternalStorageService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    account_name = models.CharField(null=False, blank=True, default="")
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
    def external_service(self):
        return self.external_storage_service

    @property
    def credentials_format(self):
        return self.external_service.credentials_format

    @property
    def credentials(self):
        if self._credentials:
            return self._credentials.as_data()
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
            self._credentials = ExternalCredentials()
        self._credentials._update(credentials_data)

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
        return [
            AddonOperationModel(_operation_imp)
            for _operation_imp in self.iter_authorized_operations()
        ]

    @property
    def authorized_operation_names(self):
        return [
            _operation_imp.declaration.name
            for _operation_imp in self.iter_authorized_operations()
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
        return build_auth_url(
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

    @transaction.atomic
    def initiate_oauth2_flow(self, authorized_scopes=None):
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            raise ValueError("Cannot initaite OAuth flow for non-OAuth credentials")
        self.oauth2_token_metadata = OAuth2TokenMetadata.objects.create(
            authorized_scopes=(
                authorized_scopes or self.external_service.supported_scopes
            ),
            state_nonce=generate_state_nonce(),
        )
        self.save()

    def iter_authorized_operations(self) -> Iterator[AddonOperationImp]:
        _addon_imp: AddonImp = self.external_storage_service.addon_imp.imp
        yield from _addon_imp.get_operation_imps(
            capabilities=self.authorized_capabilities
        )

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        validate_api_base_url(self)
        validate_oauth_state(self)
