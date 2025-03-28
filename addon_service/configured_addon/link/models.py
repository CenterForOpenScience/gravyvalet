from django.db import models

from addon_service.configured_addon.models import ConfiguredAddon


class ConfiguredLinkAddon(ConfiguredAddon):

    target_uri = models.URLField()
    target_id = models.CharField()
    int_resource_type = models.IntegerField()

    class Meta:
        verbose_name = "Configured Link Addon"
        verbose_name_plural = "Configured Link Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-link-addons"
