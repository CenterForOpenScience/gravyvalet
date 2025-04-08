"""a static (and still in progress) definition of what composes a link addon"""

import dataclasses
import enum
import typing
from collections import abc

from addon_toolkit.addon_operation_declaration import immediate_operation
from addon_toolkit.capabilities import AddonCapabilities
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.credentials import Credentials
from addon_toolkit.cursor import Cursor
from addon_toolkit.imp import AddonImp

from ._base import BaseAddonInterface


__all__ = (
    "ItemResult",
    "ItemType",
    "ItemSampleResult",
    "LinkAddonInterface",
    "LinkAddonImp",
)


class ItemType(enum.StrEnum):
    RESOURCE = enum.auto()
    FOLDER = enum.auto()


class SupportedResourceTypes(enum.Flag):
    AUDIOVISUAL = enum.auto()
    AWARD = enum.auto()
    BOOK = enum.auto()
    BOOK_CHAPTER = enum.auto()
    COLLECTION = enum.auto()
    COMPUTATIONAL_NOTEBOOK = enum.auto()
    CONFERENCE_PAPER = enum.auto()
    CONFERENCE_PROCEEDING = enum.auto()
    DATA_PAPER = enum.auto()
    DATASET = enum.auto()
    DISSERTATION = enum.auto()
    EVENT = enum.auto()
    IMAGE = enum.auto()
    INSTRUMENT = enum.auto()
    INTERACTIVE_RESOURCE = enum.auto()
    JOURNAL = enum.auto()
    JOURNAL_ARTICLE = enum.auto()
    MODEL = enum.auto()
    OUTPUT_MANAGEMENT_PLAN = enum.auto()
    PEER_REVIEW = enum.auto()
    PHYSICAL_OBJECT = enum.auto()
    PREPRINT = enum.auto()
    PROJECT = enum.auto()
    REPORT = enum.auto()
    SERVICE = enum.auto()
    SOFTWARE = enum.auto()
    SOUND = enum.auto()
    STANDARD = enum.auto()
    STUDY_REGISTRATION = enum.auto()
    TEXT = enum.auto()
    WORKFLOW = enum.auto()
    OTHER = enum.auto()


@dataclasses.dataclass
class ItemResult:
    item_id: str
    item_name: str
    item_type: ItemType
    resource_type: SupportedResourceTypes | None = None
    item_link: str | None = None


@dataclasses.dataclass
class ItemSampleResult:
    """a sample from a possibly-large population of result items"""

    items: abc.Collection[ItemResult]
    total_count: int | None = None
    this_sample_cursor: str = ""
    next_sample_cursor: str | None = None  # when None, this is the last page of results
    prev_sample_cursor: str | None = None
    first_sample_cursor: str = ""

    def with_cursor(self, cursor: Cursor) -> typing.Self:
        return dataclasses.replace(
            self,
            this_sample_cursor=cursor.this_cursor_str,
            next_sample_cursor=cursor.next_cursor_str,
            prev_sample_cursor=cursor.prev_cursor_str,
            first_sample_cursor=cursor.first_cursor_str,
        )


###
# declaration of all link addon operations


class LinkAddonInterface(BaseAddonInterface, typing.Protocol):

    async def build_url_for_id(self, item_id: str) -> str: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def get_item_info(self, item_id: str) -> ItemResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def list_root_items(self, page_cursor: str = "") -> ItemSampleResult: ...

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: ItemType | None = None,
    ) -> ItemSampleResult: ...


@dataclasses.dataclass
class LinkAddonImp(AddonImp):
    """base class for link addon implementations"""

    ADDON_INTERFACE = LinkAddonInterface


@dataclasses.dataclass
class LinkAddonHttpRequestorImp(LinkAddonImp, LinkAddonInterface):
    """base class for link addon implementations using GV network"""

    network: HttpRequestor


@dataclasses.dataclass
class LinkAddonClientRequestorImp[T](LinkAddonImp):
    """base class for link addon with custom clients"""

    client: T = dataclasses.field(init=False)
    credentials: dataclasses.InitVar[Credentials]

    def __post_init__(self, credentials):
        self.client = self.create_client(credentials)

    @staticmethod
    def create_client(credentials) -> T:
        raise NotImplementedError
