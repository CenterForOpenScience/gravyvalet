import dataclasses

from django.db import models

from addon_service.abstract.configured_addon.models import ConfiguredAddon
from addon_toolkit.interfaces.storage import StorageConfig


class ConfiguredStorageAddon(ConfiguredAddon):

    root_folder = models.CharField(blank=True)

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
    def storage_imp_config(self) -> StorageConfig:
        return dataclasses.replace(
            self.base_account.storage_imp_config,
            connected_root_id=self.root_folder,
        )
