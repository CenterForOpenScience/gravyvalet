from django.db import models

from addon_service.abstract.authorized_account.models import AuthorizedAccount
from addon_service.addon_imp.instantiation import get_citation_addon_instance
from addon_service.external_citation_service.models import ExternalCitationService
from addon_toolkit.interfaces.citation import CitationConfig


class AuthorizedCitationAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalCitationService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    default_root_folder = models.CharField(blank=True)

    external_citation_service = models.ForeignKey(
        "addon_service.ExternalCitationService",
        on_delete=models.CASCADE,
        related_name="authorized_citation_accounts",
    )

    account_owner = models.ForeignKey(
        "addon_service.UserReference",
        on_delete=models.CASCADE,
        related_name="authorized_citation_accounts",
    )
    _credentials = models.OneToOneField(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        primary_key=False,
        null=True,
        blank=True,
        related_name="authorized_citation_account",
    )
    _temporary_oauth1_credentials = models.OneToOneField(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        primary_key=False,
        null=True,
        blank=True,
        related_name="temporary_authorized_citation_account",
    )
    oauth2_token_metadata = models.ForeignKey(
        "addon_service.OAuth2TokenMetadata",
        on_delete=models.CASCADE,  # probs not
        null=True,
        blank=True,
        related_name="authorized_citation_accounts",
    )

    class Meta:
        verbose_name = "Authorized Citation Account"
        verbose_name_plural = "Authorized Citation Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-citation-accounts"

    @property
    def external_service(self) -> ExternalCitationService:
        return self.external_citation_service

    async def execute_post_auth_hook(self, auth_extras: dict | None = None):
        imp = await get_citation_addon_instance(
            self.imp_cls,
            self,
            self.citation_imp_config,
        )
        self.external_account_id = await imp.get_external_account_id(auth_extras or {})
        await self.asave()

    @property
    def citation_imp_config(self) -> CitationConfig:
        return CitationConfig(
            external_api_url=self.api_base_url,
            connected_root_id=self.default_root_folder,
            external_account_id=self.external_account_id,
        )
