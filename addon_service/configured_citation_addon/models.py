from django.db import models

from addon_service.abstract.configured_addon.models import ConfiguredAddon
from addon_toolkit.interfaces.citation import CitationConfig


class ConfiguredCitationAddon(ConfiguredAddon):

    base_account = models.ForeignKey(
        "addon_service.AuthorizedCitationAccount",
        on_delete=models.CASCADE,
        related_name="configured_citation_addons",
    )
    authorized_resource = models.ForeignKey(
        "addon_service.ResourceReference",
        on_delete=models.CASCADE,
        related_name="configured_citation_addons",
    )

    class Meta:
        verbose_name = "Configured Citation Addon"
        verbose_name_plural = "Configured Citation Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-citation-addons"

    @property
    def citation_imp_config(self) -> CitationConfig:
        return self.base_account.citation_imp_config
