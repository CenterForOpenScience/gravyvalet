"""a static (and still in progress) definition of what composes a redirect addon"""

import dataclasses

from addon_toolkit.imp import AddonImp

@dataclasses.dataclass
class RedirectAddonImp(AddonImp):
    """base class for redirect addon implementations"""
    pass