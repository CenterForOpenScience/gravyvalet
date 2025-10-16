from addon_toolkit.imp import AddonImp
from addon_toolkit.interfaces._base import BaseAddonInterface


class DummyRedirectImp(AddonImp):
    """this is a dummy AddonImp for ALL redirect services.
    redirect links will be specified in django admin configuration."""

    ADDON_INTERFACE = BaseAddonInterface
