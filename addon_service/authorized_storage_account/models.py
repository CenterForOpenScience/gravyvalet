from typing import Iterator

from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_addon_capability
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
    external_account = models.ForeignKey(
        "addon_service.ExternalAccount",
        on_delete=models.CASCADE,
        related_name="authorized_storage_accounts",
    )

    class Meta:
        verbose_name = "Authorized Storage Account"
        verbose_name_plural = "Authorized Storage Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-storage-accounts"

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
    def account_owner(self):
        return self.external_account.owner  # TODO: prefetch/select_related

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

    def iter_authorized_operations(self) -> Iterator[AddonOperationImp]:
        _addon_imp: AddonImp = self.external_storage_service.addon_imp.imp
        yield from _addon_imp.get_operation_imps(
            capabilities=self.authorized_capabilities
        )
