import dataclasses

from django.db import models

from addon_service.configured_addon.models import ConfiguredAddon
from addon_toolkit.interfaces.storage import StorageConfig


class ConfiguredStorageAddon(ConfiguredAddon):

    root_folder = models.CharField(blank=True)

    class Meta:
        verbose_name = "Configured Storage Addon"
        verbose_name_plural = "Configured Storage Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-storage-addons"

    @property
    def config(self) -> StorageConfig:
        return dataclasses.replace(
            self.base_account.authorizedstorageaccount.config,
            connected_root_id=self.root_folder,
        )
