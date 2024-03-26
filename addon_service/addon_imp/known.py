"""the single static source of truth for addon implementations known to the addon service

import and add new implementations here to make them available in the api
"""
import enum

from addon_imps.storage import box_dot_com
from addon_toolkit import AddonImp
from addon_toolkit.storage import StorageAddon


__all__ = (
    "get_imp_by_name",
    "get_imp_name",
    "get_imp_by_number",
)


@enum.unique
class KnownAddonImp(enum.Enum):
    """enum with a name for each addon implementation class that should be known to the api"""

    BOX_DOT_COM = AddonImp(
        StorageAddon,
        imp_cls=box_dot_com.BoxDotComStorage,
        imp_number=1,
    )


###
# helpers for accessing KnownAddonImp


def get_imp_by_name(imp_name: str) -> AddonImp:
    return KnownAddonImp[imp_name].value


def get_imp_name(imp: AddonImp) -> str:
    return KnownAddonImp(imp).name


def get_imp_by_number(imp_number: int) -> AddonImp:
    for _enum_imp in KnownAddonImp:
        if _enum_imp.value.imp_number == imp_number:
            return _enum_imp.value
    raise KeyError


if __debug__:
    from collections import Counter

    _repeated_imp_numbers = [
        _imp_number
        for (_imp_number, _count) in Counter(
            _imp_enum.value.imp_number for _imp_enum in KnownAddonImp
        ).items()
        if _count > 1
    ]
    assert not _repeated_imp_numbers, f"repeated imp numbers!? {_repeated_imp_numbers}"
