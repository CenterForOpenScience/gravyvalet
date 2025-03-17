from django.db import models

from addon_service.authorized_account.models import AuthorizedAccount
from addon_service.configured_addon.link.models import ConfiguredLinkAddon
from addon_toolkit.interfaces.link import LinkConfig


class AuthorizedLinkAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    default_root_folder = models.CharField(blank=True)

    class Meta:
        verbose_name = "Authorized Link Account"
        verbose_name_plural = "Authorized Link Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-link-accounts"

    @property
    def configured_link_addons(self):
        return ConfiguredLinkAddon.objects.filter(base_account=self)

    @property
    def config(self) -> LinkConfig:
        return LinkConfig(
            external_api_url=self.api_base_url,
            connected_root_id=self.default_root_folder,
            external_account_id=self.external_account_id,
        )
