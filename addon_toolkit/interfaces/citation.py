import dataclasses
import typing
from enum import (
    Enum,
    auto,
)


__all__ = (
    "ItemResult",
    "ItemSampleResult",
    "CitationConfig",
    "ItemType",
    "RootItemResult",
    "CitationServiceInterface",
    "CitationAddonImp",
)

from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    BaseAddonInterface,
    immediate_operation,
)
from addon_toolkit.constrained_network.http import HttpRequestor


@dataclasses.dataclass(frozen=True)
class CitationConfig:
    external_api_url: str
    connected_root_id: str | None = None
    external_account_id: str | None = None


class ItemType(Enum):
    DOCUMENT = auto()
    COLLECTION = auto()


@dataclasses.dataclass(slots=True)
class RootItemResult:
    item_id: int
    item_name: str
    item_type: ItemType
    item_path: typing.Optional[typing.List[str]] = None


@dataclasses.dataclass
class ItemResult(RootItemResult, slots=True):
    csl: dict | None = None


@dataclasses.dataclass
class ItemSampleResult:
    items: typing.List[RootItemResult]
    total_count: typing.Optional[int] = None
    next_sample_cursor: str | None = None
    prev_sample_cursor: str | None = None


# TODO: Merge My library and documents pickers into one picker (Zotero)
# TODO: Migrate CSL compilation to backend


class CitationServiceInterface(BaseAddonInterface):

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    def list_root_collections(self) -> ItemSampleResult:
        """Lists directories (or collections) inside root"""

    @immediate_operation(capability=AddonCapabilities.ACCESS)
    def list_collection_items(
        self, collection_id: str, filter_items: ItemType | None = None
    ) -> ItemSampleResult:
        """Lists directories (or collections) and sources (books) inside root"""


@dataclasses.dataclass(frozen=True)
class CitationAddonImp(AddonImp):
    """base class for storage addon implementations"""

    ADDON_INTERFACE = CitationServiceInterface

    config: CitationConfig
    network: HttpRequestor
