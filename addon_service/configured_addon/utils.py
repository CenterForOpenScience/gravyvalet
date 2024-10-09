from __future__ import annotations

from typing import TYPE_CHECKING

from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.storage import StorageAddonImp


if TYPE_CHECKING:
    from addon_service.configured_addon.models import ConfiguredAddon


def get_config_for_addon(addon: ConfiguredAddon):
    if issubclass(addon.imp_cls, StorageAddonImp):
        return addon.configuredstorageaddon.config
    elif issubclass(addon.imp_cls, CitationAddonImp):
        return addon.configuredcitationaddon.config

    raise ValueError(f"this function implementation does not support {addon.imp_cls}")
