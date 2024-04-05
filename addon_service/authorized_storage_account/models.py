from functools import cached_property
from typing import Iterator

from django.contrib.postgres.fields import ArrayField
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
from addon_service.oauth.utils import build_auth_url
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    AddonOperationImp,
)


class AuthorizedStorageAccount(AddonsServiceBaseModel):
    int_authorized_capabilities = ArrayField(
        models.IntegerField(validators=[validate_addon_capability])
    )
    default_root_folder = models.CharField(blank=True)

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

    class Meta:
        verbose_name = "Authorized Storage Account"
        verbose_name_plural = "Authorized Storage Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-storage-accounts"

    @cached_property
    def external_service(self):
        return self.external_storage_service

    @cached_property
    def credentials_format(self):
        return self.external_service.credentials_format

    @property
    def credentials(self):
        if self._credentials:
            return self._credentials.as_data()
        return None

    @property
    def authorized_capabilities(self) -> list[AddonCapabilities]:
        """get the enum representation of int_authorized_capabilities"""
        return [
            AddonCapabilities(_int_capability)
            for _int_capability in self.int_authorized_capabilities
        ]

    @authorized_capabilities.setter
    def authorized_capabilities(self, new_capabilities: list[AddonCapabilities]):
        """set int_authorized_capabilities without caring it's int"""
        self.int_authorized_capabilities = [
            AddonCapabilities(_cap).value for _cap in new_capabilities
        ]

    @property
    def owner_uri(self) -> str:
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
            _operation_imp.operation.name
            for _operation_imp in self.iter_authorized_operations()
        ]

    @property
    def auth_url(self) -> str:
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            return None

        state_token = self.credentials.state_token
        if not state_token:
            return None
        return build_auth_url(
            auth_uri=self.external_service.oauth2_client_config.auth_uri,
            client_id=self.external_service.oauth2_client_config.client_id,
            state_token=state_token,
            authorized_scopes=self.credentials.authorized_scopes,
            redirect_uri=self.external_service.auth_callback_url,
        )

    @transaction.atomic
    def set_credentials(self, api_credentials_blob=dict, authorized_scopes=None):
        known_credentials = self.credentials
        if known_credentials:
            self._credentials._update(api_credentials_blob)
            return

        if self.credentials_format is CredentialsFormats.OAUTH2:
            _credentials = ExternalCredentials.initiate_oauth2_flow(
                authorized_scopes or self.external_service.default_scopes
            )
        else:
            _credentials = ExternalCredentials.from_api_blob(api_credentials_blob)
        self._credentials = _credentials
        self.save()
        _credentials.save()  # validate

    def iter_authorized_operations(self) -> Iterator[AddonOperationImp]:
        _addon_imp: AddonImp = self.external_storage_service.addon_imp.imp
        yield from _addon_imp.get_operation_imps(
            capabilities=self.authorized_capabilities
        )
