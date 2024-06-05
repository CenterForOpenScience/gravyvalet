import dataclasses

from django.core.exceptions import ValidationError
from django.db import models

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.validators import validate_addon_capability
from addon_service.resource_reference.models import ResourceReference
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
)
from addon_toolkit.interfaces.storage import StorageConfig


class ConnectedStorageAddonManager(models.Manager):

    def active(self):
        """filter to addons owned by non-deactivated users"""
        return self.get_queryset().filter(
            base_account__account_owner__deactivated__isnull=True
        )


class ConfiguredStorageAddon(AddonsServiceBaseModel):
    objects = ConnectedStorageAddonManager()

    root_folder = models.CharField(blank=True)

    int_connected_capabilities = models.IntegerField(
        validators=[validate_addon_capability]
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
    def connected_capabilities(self) -> AddonCapabilities:
        """get the enum representation of int_connected_capabilities"""
        return AddonCapabilities(self.int_connected_capabilities)

    @connected_capabilities.setter
    def connected_capabilities(self, new_capabilities: AddonCapabilities):
        """set int_connected_capabilities without caring it's int"""
        self.int_connected_capabilities = new_capabilities.value

    @property
    def account_owner(self):
        return self.base_account.account_owner

    @property
    def owner_uri(self) -> str:
        return self.base_account.owner_uri

    @property
    def resource_uri(self):
        return self.authorized_resource.resource_uri

    @resource_uri.setter
    def resource_uri(self, uri: str):
        _resource_ref, _ = ResourceReference.objects.get_or_create(resource_uri=uri)
        self.authorized_resource = _resource_ref

    @property
    def connected_operations(self) -> list[AddonOperationModel]:
        _imp_cls = self.imp_cls
        return [
            AddonOperationModel(_imp_cls, _operation)
            for _operation in _imp_cls.implemented_operations_for_capabilities(
                self.connected_capabilities
            )
        ]

    @property
    def connected_operation_names(self):
        return [
            _operation.name
            for _operation in self.imp_cls.implemented_operations_for_capabilities(
                self.connected_capabilities
            )
        ]

    @property
    def credentials(self):
        return self.base_account.credentials

    @property
    def external_service(self):
        return self.base_account.external_service

    @property
    def imp_cls(self) -> type[AddonImp]:
        return self.base_account.imp_cls

    def storage_imp_config(self) -> StorageConfig:
        return dataclasses.replace(
            self.base_account.storage_imp_config(),
            connected_root_id=self.root_folder,
        )

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
