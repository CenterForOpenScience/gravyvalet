from django.db import models

from addon_service.addon_imp.instantiation import get_citation_addon_instance
from addon_service.authorized_account.models import AuthorizedAccount
from addon_toolkit.interfaces.citation import CitationConfig


class AuthorizedCitationAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalCitationService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    default_root_folder = models.CharField(blank=True)

    class Meta:
        verbose_name = "Authorized Citation Account"
        verbose_name_plural = "Authorized Citation Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-citation-accounts"

    async def execute_post_auth_hook(self, auth_extras: dict | None = None):
        imp = await get_citation_addon_instance(
            self.imp_cls,
            self,
            self.config,
        )
        self.external_account_id = await imp.get_external_account_id(auth_extras or {})
        await self.asave()

    @property
    def config(self) -> CitationConfig:
        return CitationConfig(
            external_api_url=self.api_base_url,
            connected_root_id=self.default_root_folder,
            external_account_id=self.external_account_id,
        )
