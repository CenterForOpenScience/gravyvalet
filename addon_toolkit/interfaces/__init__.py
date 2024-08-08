import enum

from . import storage
from ._base import BaseAddonInterface


__all__ = (
    "AllAddonInterfaces",
    "BaseAddonInterface",
    "storage",
)


class AllAddonInterfaces(enum.Enum):
    STORAGE = storage.StorageAddonInterface
