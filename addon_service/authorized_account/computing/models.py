from addon_service.addon_imp.instantiation import get_computing_addon_instance
from addon_service.authorized_account.models import AuthorizedAccount
from addon_toolkit.interfaces.computing import ComputingConfig


class AuthorizedComputingAccount(AuthorizedAccount):
    """Model for describing a user's account on an ExternalComputingService.

    This model collects all of the information required to actually perform remote
    operations against the service and to aggregate accounts under a known user.
    """

    class Meta:
        verbose_name = "Authorized Computing Account"
        verbose_name_plural = "Authorized Computing Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-computing-accounts"

    async def execute_post_auth_hook(self, auth_extras: dict | None = None):
        imp = await get_computing_addon_instance(
            self.imp_cls,
            self,
            self.config,
        )
        self.external_account_id = await imp.get_external_account_id(auth_extras or {})
        await self.asave()

    @property
    def config(self) -> ComputingConfig:
        return ComputingConfig(
            external_api_url=self.api_base_url,
            external_account_id=self.external_account_id,
        )
