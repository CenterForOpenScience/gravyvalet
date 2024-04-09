from typing import Iterator

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_addon_capability
from addon_toolkit import (
    AddonCapabilities,
    AddonOperationImp,
)


class ConnectedStorageAddonManager(models.Manager):
    """
    Only returned active users, not ones that are deactivated.
    """

    def active(self):
        return self.get_queryset().filter(
            base_account__account_owner__deactivated__isnull=True
        )


class ConfiguredStorageAddon(AddonsServiceBaseModel):
    objects = ConnectedStorageAddonManager()

    root_folder = models.CharField(blank=True)

    int_connected_capabilities = ArrayField(
        models.IntegerField(validators=[validate_addon_capability])
    )

    base_account = models.ForeignKey(
        "addon_service.AuthorizedStorageAccount",
        on_delete=models.CASCADE,
        related_name="configured_storage_addons",
    )
    authorized_resource = models.ForeignKey(
        "addon_service.ResourceReference",
        on_delete=models.CASCADE,
        related_name="configured_storage_addons",
    )

    class Meta:
        verbose_name = "Configured Storage Addon"
        verbose_name_plural = "Configured Storage Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-storage-addons"

    @property
    def connected_capabilities(self) -> list[AddonCapabilities]:
        """get the enum representation of int_connected_capabilities"""
        return [
            AddonCapabilities(_int_capability)
            for _int_capability in self.int_connected_capabilities
        ]

    @connected_capabilities.setter
    def connected_capabilities(self, new_capabilities: list[AddonCapabilities]):
        """set int_connected_capabilities without caring it's int"""
        self.int_connected_capabilities = [
            AddonCapabilities(_cap).value for _cap in new_capabilities
        ]

    @property
    def account_owner(self):
        return self.base_account.account_owner

    @property
    def owner_uri(self) -> str:
        return self.base_account.owner_uri

    @property
    def resource_uri(self):
        return self.authorized_resource.resource_uri

    @property
    def connected_operations(self) -> list[AddonOperationModel]:
        return [
            AddonOperationModel(_operation_imp)
            for _operation_imp in self.iter_connected_operations()
        ]

    @property
    def connected_operation_names(self):
        return [
            _operation_imp.operation.name
            for _operation_imp in self.iter_connected_operations()
        ]

    def iter_connected_operations(self) -> Iterator[AddonOperationImp]:
        _connected_caps = self.connected_capabilities
        for _operation_imp in self.base_account.iter_authorized_operations():
            if _operation_imp.operation.capability in _connected_caps:
                yield _operation_imp

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        _connected_caps = set(self.connected_capabilities)
        if not _connected_caps.issubset(self.base_account.authorized_capabilities):
            _unauthorized_caps = _connected_caps.difference(
                self.base_account.authorized_capabilities
            )
            raise ValidationError(
                {
                    "connected_capabilities": f"capabilities not authorized on account: {_unauthorized_caps}",
                }
            )
