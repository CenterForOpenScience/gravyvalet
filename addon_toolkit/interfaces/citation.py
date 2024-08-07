import dataclasses
import typing

from addon_toolkit.imp import AddonImp

from ._base import BaseAddonInterface


__all__ = (
    "CitationConfig",
    "CitationAddonInterface",
    "CitationAddonImp",
)


@dataclasses.dataclass(frozen=True, slots=True)
class CitationConfig:
    external_api_url: str
    connected_root_id: str | None = None
    external_account_id: str | None = None


class CitationAddonInterface(BaseAddonInterface, typing.Protocol):
    pass


@dataclasses.dataclass(frozen=True)
class CitationAddonImp(AddonImp):
    """base class for citation addon implementations"""
