import enum

from . import (
    citation,
    computing,
    storage,
    link,
)
from ._base import BaseAddonInterface


__all__ = (
    "AllAddonInterfaces",
    "BaseAddonInterface",
    "storage",
    "citation",
    "computing",
    "link",
)


class AllAddonInterfaces(enum.Enum):
    STORAGE = storage.StorageAddonInterface
    CITATION = citation.CitationServiceInterface
    COMPUTING = computing.ComputingAddonInterface
    LINK = link.LinkAddonInterface
