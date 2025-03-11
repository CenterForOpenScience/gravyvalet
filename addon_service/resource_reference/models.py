from django.db import models
from django.db.models.functions import Lower

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.configured_addon.citation.models import ConfiguredCitationAddon
from addon_service.configured_addon.computing.models import ConfiguredComputingAddon
from addon_service.configured_addon.storage.models import ConfiguredStorageAddon
from addon_service.configured_addon.link.models import ConfiguredLinkAddon


class ResourceReference(AddonsServiceBaseModel):
    resource_uri = models.URLField(unique=True, db_index=True, null=False)

    @property
    def configured_storage_addons(self):
        return (
            ConfiguredStorageAddon.objects.filter(authorized_resource=self)
            .select_related(
                "base_account__external_service__externalstorageservice",
                "base_account__authorizedstorageaccount",
                "base_account__account_owner",
            )
            .order_by(Lower("_display_name"))
        )

    @property
    def configured_citation_addons(self):
        return ConfiguredCitationAddon.objects.filter(
            authorized_resource=self
        ).select_related(
            "base_account__external_service__externalcitationservice",
            "base_account__authorizedcitationaccount",
            "base_account__account_owner",
        )

    @property
    def configured_computing_addons(self):
        return ConfiguredComputingAddon.objects.filter(
            authorized_resource=self
        ).select_related(
            "base_account__external_service__externalcomputingservice",
            "base_account__authorizedcitationaccount",
            "base_account__account_owner",
        )

    @property
    def configured_link_addons(self):
        return (
            ConfiguredLinkAddon.objects.filter(authorized_resource=self)
            .select_related(
                "base_account__external_service__externallinkservice",
                "base_account__authorizedlinkaccount",
                "base_account__account_owner",
            )
            .order_by(Lower("_display_name"))
        )

    class Meta:
        verbose_name = "Resource Reference"
        verbose_name_plural = "Resource References"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "resource-references"
