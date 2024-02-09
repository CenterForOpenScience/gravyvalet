from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_toolkit import IntAddonCapability


class ConfiguredStorageAddon(AddonsServiceBaseModel):
    root_folder = models.CharField()

    connected_capabilities = ArrayField(
        models.IntegerField(choices=IntAddonCapability.as_django_choices()),
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
    def account_owner(self):
        return self.base_account.external_account.owner
