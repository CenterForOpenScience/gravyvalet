"""what a base StorageAddon could be like (incomplete)"""
import collections.abc
import dataclasses
import typing

# note: addon_toolkit.storage is down-import-stream from addon_toolkit
from addon_toolkit import (
    AddonCapabilities,
    RedirectResult,
    addon_protocol,
    immediate_operation,
    redirect_operation,
)
from addon_toolkit.constrained_http import HttpRequestor
from addon_toolkit.cursor import Cursor


__all__ = ("StorageAddon",)


###
# use dataclasses for operation args and return values


@dataclasses.dataclass(frozen=True)
class StorageConfig:
    max_upload_mb: int


@dataclasses.dataclass
class ItemResult:
    item_id: str
    item_name: str
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
    this_sample_cursor: str = ""
    next_sample_cursor: str | None = None  # when None, this is the last page of results
    prev_sample_cursor: str | None = None
    first_sample_cursor: str = ""

    # optional init var:
    cursor: dataclasses.InitVar[Cursor | None] = None

    def __post_init__(self, cursor: Cursor | None):
        if cursor is not None:
            self.this_sample_cursor = cursor.this_cursor_str
            self.next_sample_cursor = cursor.next_cursor_str
            self.prev_sample_cursor = cursor.prev_cursor_str
            self.first_sample_cursor = cursor.first_cursor_str


@addon_protocol()  # TODO: descriptions with language tags
@dataclasses.dataclass(frozen=True)
class StorageAddon(typing.Protocol):
    # context provided on `self` to operation implementations:
    config: StorageConfig
    network: HttpRequestor

    @redirect_operation(capability=AddonCapabilities.ACCESS)
    def download(self, item_id: str) -> RedirectResult:
        ...

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
    async def get_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_parent_item_id(self, item_id: str) -> PossibleSingleItemResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_item_path(self, item_id: str) -> PathResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
    ) -> ItemSampleResult:
        ...


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
