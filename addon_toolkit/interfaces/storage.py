"""a static (and still in progress) definition of what composes a storage addon"""

import dataclasses
import enum
import typing
from abc import abstractmethod
from collections import abc

from addon_toolkit.addon_operation_declaration import immediate_operation
from addon_toolkit.capabilities import AddonCapabilities
from addon_toolkit.constrained_network import HttpRequestor
from addon_toolkit.credentials import Credentials
from addon_toolkit.cursor import Cursor
from addon_toolkit.imp import AddonImp

from ._base import AddonInterface


__all__ = (
    "ItemResult",
    "ItemSampleResult",
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
    item_path: abc.Sequence[typing.Self] | None = None


@dataclasses.dataclass
class PossibleSingleItemResult:
    possible_item: ItemResult | None


@dataclasses.dataclass
class ItemSampleResult:
    """a sample from a possibly-large population of result items"""

    items: abc.Collection[ItemResult]
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
    # single-item operations:

    # @redirect_operation(capability=AddonCapabilities.ACCESS)
    # def download(self, item_id: str) -> RedirectResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_item_info(self, item_id: str) -> ItemResult: ...

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
    # tree-read operations:

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def list_root_items(self, page_cursor: str = "") -> ItemSampleResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def list_child_items(
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


@dataclasses.dataclass
class StorageAddonImp(AddonImp):
    """base class for storage addon implementations"""

    ADDON_INTERFACE = StorageAddonInterface

    config: StorageConfig


@dataclasses.dataclass
class StorageAddonHttpRequestorImp(StorageAddonImp):
    """base class for storage addon implementations using GV network"""

    network: HttpRequestor


@dataclasses.dataclass
class StorageAddonClientRequestorImp(StorageAddonImp):
    """base class for storage addon with custom clients"""

    client: typing.Any = dataclasses.field(init=False)
    credentials: dataclasses.InitVar[Credentials]

    def __post_init__(self, credentials):
        self.client = self.create_client(credentials)

    @abstractmethod
    def create_client(self, credentials):
        raise NotImplementedError
