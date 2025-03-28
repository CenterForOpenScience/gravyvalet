from addon_service.authorized_account.models import AuthorizedAccount
from addon_service.configured_addon.link.models import ConfiguredLinkAddon


class AuthorizedLinkAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    class Meta:
        verbose_name = "Authorized Link Account"
        verbose_name_plural = "Authorized Link Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-link-accounts"

    @property
    def configured_link_addons(self):
        return ConfiguredLinkAddon.objects.filter(base_account=self).select_related(
            "authorized_resource"
        )
