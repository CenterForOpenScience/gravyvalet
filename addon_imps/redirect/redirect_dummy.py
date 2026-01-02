from addon_toolkit.interfaces._base import BaseAddonInterface
from addon_toolkit.interfaces.redirect import RedirectAddonImp


class DummyRedirectImp(RedirectAddonImp):
    """this is a dummy AddonImp for ALL redirect services.
    redirect links will be specified in django admin configuration."""

    ADDON_INTERFACE = BaseAddonInterface
