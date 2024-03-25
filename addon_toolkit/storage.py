"""what a base StorageAddon could be like (incomplete)"""
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


__all__ = ("StorageAddon",)


###
# use dataclasses for operation args and return values


@dataclasses.dataclass
class StorageConfig:
    max_upload_mb: int


@dataclasses.dataclass
class PossibleSingleItemResult:
    possible_item_id: str | None


@dataclasses.dataclass
class ManyItemResult:
    """representing a sample of items from a possibly large result set"""

    item_ids: list[str]
    total_count: int = 0
    this_page_cursor: str = ""  # empty cursor when all results fit on one page
    next_page_cursor: str | None = None
    prev_page_cursor: str | None = None
    init_page_cursor: str | None = None

    def __post_init__(self):
        if (
            (self.total_count == 0)
            and (self.next_page_cursor is None)
            and self.item_ids
        ):
            self.total_count = len(self.item_ids)


@addon_protocol()  # TODO: descriptions with language tags
@dataclasses.dataclass
class StorageAddon(typing.Protocol):
    config: StorageConfig

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
    async def get_root_item_ids(self, page_cursor: str = "") -> ManyItemResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_parent_item_id(self, item_id: str) -> PossibleSingleItemResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_item_path(self, item_id: str) -> str:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_child_item_ids(
        self,
        item_id: str,
        page_cursor: str = "",
    ) -> ManyItemResult:
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
