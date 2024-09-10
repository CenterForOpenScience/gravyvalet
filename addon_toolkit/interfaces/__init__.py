import enum

from . import (
    citation,
    computing,
    storage,
)
from ._base import BaseAddonInterface


__all__ = (
    "AllAddonInterfaces",
    "BaseAddonInterface",
    "storage",
    "citation",
    "computing",
)


class AllAddonInterfaces(enum.Enum):
    STORAGE = storage.StorageAddonInterface
    CITATION = citation.CitationServiceInterface
    COMPUTING = computing.ComputingAddonInterface
