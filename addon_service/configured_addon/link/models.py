import dataclasses

from django.db import models

from addon_service.configured_addon.models import ConfiguredAddon
from addon_toolkit.interfaces.link import LinkConfig


class ConfiguredLinkAddon(ConfiguredAddon):

    root_folder = models.CharField(blank=True)

    class Meta:
        verbose_name = "Configured Link Addon"
        verbose_name_plural = "Configured Link Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-link-addons"

    @property
    def config(self) -> LinkConfig:
        return dataclasses.replace(
            self.base_account.authorizedlinkaccount.config,
            connected_root_id=self.root_folder,
        )
