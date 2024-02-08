from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ResourceReference(AddonsServiceBaseModel):
    resource_uri = models.URLField(unique=True, db_index=True, null=False)

    class Meta:
        verbose_name = "Resource Reference"
        verbose_name_plural = "Resource References"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "resource-references"
