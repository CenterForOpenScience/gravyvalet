from django.db import models

from addon_service.authorized_account.models import AuthorizedAccount
from addon_service.configured_addon.storage.models import ConfiguredStorageAddon
from addon_toolkit.interfaces.storage import StorageConfig


class AuthorizedStorageAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    default_root_folder = models.CharField(blank=True)

    class Meta:
        verbose_name = "Authorized Storage Account"
        verbose_name_plural = "Authorized Storage Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-storage-accounts"

    @property
    def configured_storage_addons(self):
        return ConfiguredStorageAddon.objects.filter(base_account=self)

    @property
    def config(self) -> StorageConfig:
        return StorageConfig(
            max_upload_mb=self.external_service.externalstorageservice.max_upload_mb,
            external_api_url=self.api_base_url,
            connected_root_id=self.default_root_folder,
            external_account_id=self.external_account_id,
        )
