from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.configured_addon.storage.models import ConfiguredStorageAddon


class ResourceReference(AddonsServiceBaseModel):
    resource_uri = models.URLField(unique=True, db_index=True, null=False)

    @property
    def configured_storage_addons(self):
        return ConfiguredStorageAddon.objects.filter(authorized_resource=self)

    class Meta:
        verbose_name = "Resource Reference"
        verbose_name_plural = "Resource References"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "resource-references"
