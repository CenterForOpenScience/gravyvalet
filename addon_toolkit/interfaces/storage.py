"""a static (and still in progress) definition of what composes a storage addon"""

import collections.abc
import dataclasses
import enum
import typing

from addon_toolkit.addon_operation_declaration import (
    immediate_operation,
    redirect_operation,
)
from addon_toolkit.addon_operation_results import RedirectResult
from addon_toolkit.capabilities import AddonCapabilities
from addon_toolkit.constrained_network import HttpRequestor
from addon_toolkit.cursor import Cursor
from addon_toolkit.imp import AddonImp

from ._base import AddonInterface


__all__ = (
    "ItemResult",
    "ItemSampleResult",
    "PathResult",
    "PossibleSingleItemResult",
    "StorageAddonInterface",
    "StorageAddonImp",
    "StorageConfig",
)


###
# dataclasses used for operation args and return values


@dataclasses.dataclass(frozen=True)
class StorageConfig:
    max_upload_mb: int
    external_api_url: str
    connected_root_id: str | None = None
    external_account_id: str | None = None


class ItemType(enum.Enum):
    FILE = enum.auto()
    FOLDER = enum.auto()


@dataclasses.dataclass
class ItemResult:
    item_id: str
    item_name: str
    item_type: ItemType
    item_path: list[str] | None = None


@dataclasses.dataclass
class PathResult:
    ancestor_ids: collections.abc.Sequence[str]  # most distant first


@dataclasses.dataclass
class PossibleSingleItemResult:
    possible_item: ItemResult | None


@dataclasses.dataclass
class ItemSampleResult:
    """a sample from a possibly-large population of result items"""

    items: collections.abc.Collection[ItemResult]
    total_count: int | None = None
    this_sample_cursor: str = ""
    next_sample_cursor: str | None = None  # when None, this is the last page of results
    prev_sample_cursor: str | None = None
    first_sample_cursor: str = ""

    # optional init var:
    cursor: dataclasses.InitVar[Cursor | None] = None

    def __post_init__(self, cursor: Cursor | None) -> None:
        if cursor is not None:
            self.this_sample_cursor = cursor.this_cursor_str
            self.next_sample_cursor = cursor.next_cursor_str
            self.prev_sample_cursor = cursor.prev_cursor_str
            self.first_sample_cursor = cursor.first_cursor_str


###
# declaration of all storage addon operations


class StorageAddonInterface(AddonInterface, typing.Protocol):

    ###
    # declared operations:

    @redirect_operation(capability=AddonCapabilities.ACCESS)
    def download(self, item_id: str) -> RedirectResult: ...

    #
    #    @immediate_operation(capability=AddonCapabilities.ACCESS)
    #    async def get_item_description(self, item_id: str) -> dict: ...
    #
    #    ##
    #    # "item-write" operations:
    #
    #    @redirect_operation(capability=AddonCapabilities.UPDATE)
    #    def item_upload_url(self, item_id: str) -> str: ...
    #
    #    @immediate_operation(capability=AddonCapabilities.UPDATE)
    #    async def pls_delete_item(self, item_id: str): ...
    #

    ##
    # "tree-read" operations:

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_root_folders(self, page_cursor: str = "") -> ItemSampleResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_root_items(self, page_cursor: str = "") -> ItemSampleResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_parent_item_id(self, item_id: str) -> PossibleSingleItemResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_item_path(self, item_id: str) -> PathResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: ItemType | None = None,
    ) -> ItemSampleResult: ...


#
#    ##
#    # "tree-write" operations
#
#    @immediate_operation(capability=AddonCapabilities.UPDATE)
#    async def pls_move_item(self, item_id: str, new_treepath: str): ...
#
#    @immediate_operation(capability=AddonCapabilities.UPDATE)
#    async def pls_copy_item(self, item_id: str, new_treepath: str): ...
#
#    ##
#    # "version-read" operations
#
#    @immediate_operation(capability=AddonCapabilities.ACCESS)
#    async def get_current_version_id(self, item_id: str) -> str: ...
#
#    @immediate_operation(capability=AddonCapabilities.ACCESS)
#    async def get_version_ids(self, item_id: str) -> PagedResult: ...
#
#    ##
#    # "version-write" operations
#
#    @immediate_operation(capability=AddonCapabilities.UPDATE)
#    async def pls_restore_version(self, item_id: str, version_id: str): ...


@dataclasses.dataclass(frozen=True)
class StorageAddonImp(AddonImp):
    """base class for storage addon implementations"""

    ADDON_INTERFACE = StorageAddonInterface

    config: StorageConfig
    network: HttpRequestor
