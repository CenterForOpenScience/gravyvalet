from addon_service.common.known_imps import AddonImpNumbers
from addon_service.configured_addon.models import ConfiguredAddon
from addon_toolkit.interfaces.computing import ComputingConfig


class ConfiguredComputingAddon(ConfiguredAddon):

    class Meta:
        verbose_name = "Configured Computing Addon"
        verbose_name_plural = "Configured Computing Addons"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "configured-computing-addons"

    @property
    def config(self) -> ComputingConfig:
        return self.base_account.authorizedcomputingaccount.config

    @property
    def external_service_name(self) -> str:
        number = self.base_account.external_service.int_addon_imp
        return AddonImpNumbers(number).name.lower()
