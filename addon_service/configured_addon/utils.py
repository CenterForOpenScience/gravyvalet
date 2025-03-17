from __future__ import annotations

from typing import TYPE_CHECKING

from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.computing import ComputingAddonImp
from addon_toolkit.interfaces.storage import StorageAddonImp
from addon_toolkit.interfaces.link import LinkAddonImp


if TYPE_CHECKING:
    from addon_service.configured_addon.models import ConfiguredAddon


def get_config_for_addon(addon: ConfiguredAddon):
    if issubclass(addon.imp_cls, StorageAddonImp):
        return addon.configuredstorageaddon.config
    elif issubclass(addon.imp_cls, CitationAddonImp):
        return addon.configuredcitationaddon.config
    elif issubclass(addon.imp_cls, ComputingAddonImp):
        return addon.configuredcomputingaddon.config
    elif issubclass(addon.imp_cls, LinkAddonImp):
        return addon.configuredlinkaddon.config

    raise ValueError(f"this function implementation does not support {addon.imp_cls}")
