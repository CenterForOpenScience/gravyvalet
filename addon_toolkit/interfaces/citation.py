import dataclasses
import typing

from addon_toolkit.imp import AddonImp

from ._base import BaseAddonInterface


__all__ = (
    "CitationConfig",
    "CitationAddonInterface",
    "CitationAddonImp",
)


@dataclasses.dataclass(frozen=True)
class CitationConfig:
    pass


class CitationAddonInterface(BaseAddonInterface, typing.Protocol):
    pass


@dataclasses.dataclass(frozen=True)
class CitationAddonImp(AddonImp):
    """base class for citation addon implementations"""
