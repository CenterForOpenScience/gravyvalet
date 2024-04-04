"""what a base StorageAddonProtocol could be like (incomplete)"""
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


__all__ = ("StorageAddonProtocol",)


###
# use dataclasses for operation args and return values


@dataclasses.dataclass
class PagedResult:
    item_ids: list[str]
    total_count: int = 0
    next_cursor: str | None = None

    def __post_init__(self):
        if (self.total_count == 0) and (self.next_cursor is None) and self.item_ids:
            self.total_count = len(self.item_ids)


@dataclasses.dataclass
class PageArg:
    cursor: str = ""


@dataclasses.dataclass
class ItemArg:
    item_id: str


@addon_protocol()
class StorageAddonProtocol(typing.Protocol):
    @redirect_operation(capability=AddonCapabilities.ACCESS)
    def download(self, item: ItemArg) -> RedirectResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    def blargblarg(self, item: ItemArg) -> PagedResult:
        ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    def opop(self, item: ItemArg, page: PageArg) -> PagedResult:
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
    async def get_root_item_ids(self, page: PageArg) -> PagedResult:
        ...

    #
    #    @immediate_operation(capability=AddonCapabilities.ACCESS)
    #    async def get_parent_item_id(self, item_id: str) -> str | None: ...
    #
    #    @immediate_operation(capability=AddonCapabilities.ACCESS)
    #    async def get_item_path(self, item_id: str) -> str: ...
    #
    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_child_item_ids(self, item: ItemArg, page: PageArg) -> PagedResult:
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
