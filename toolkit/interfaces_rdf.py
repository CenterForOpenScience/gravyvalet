import dataclasses
import inspect

from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)


GRAVY = rdf.IriNamespace("https://gravyvalet.example/vocab/")


storage_norms = gather.GatheringNorms(
    focustype_iris={
        GRAVY.Item,
    },
    thesaurus={
        GRAVY.item_id: {
            rdf.TYPE: {GRAVY.ImmediateCapability},
        },
        GRAVY.item_download_url: {  # DCAT?
            rdf.TYPE: {GRAVY.RedirectCapability},
        },
        GRAVY.get_item_description: {
            rdf.TYPE: {GRAVY.ProxyCapability},
        },
        GRAVY.do_delete_item: {
            rdf.TYPE: {GRAVY.ActionCapability},
        },
    },
)


@storage_norms.gatherer(GRAVY.item_id)
def gather_item_id(item_focus: gather.Focus):
    raise NotImplementedError


@storage_norms.gatherer(
    GRAVY.item_download_url,
    kwargs={
        "item_id": GRAVY.item_id,
    },
)
def gather_download_url(item_focus, item_id):
    return f"http://foo.example/download{item_id}"


@storage_norms.async_gatherer(
    GRAVY.get_item_description,
    kwargs={
        "item_id": GRAVY.item_id,
    },
)
async def gather_item_description(item_focus, item_id):
    # _resp = await fetch(...)
    # yield from ...
    raise NotImplementedError


@dataclasses.dataclass
class StorageInterface:
    # attrs on `self` when your StorageInterface subclass is instantiated
    authorized_account: AuthorizedStorageAccount
    configured_addon: ConfiguredStorageAddon

    ##
    # "read" capabilities:

    # def item_download_url(self, item_id: str) -> str:
    # async def get_item_description(self, item_id: str) -> dict:

    ##
    # "write" capabilities:

    # def item_upload_url(self, item_id: str) -> str:
    # async def do_delete_item(self, item_id: str):

    ##
    # "tree-read" capabilities:

    # async def get_root_item_ids(self) -> PagedResult[str]:
    # async def get_parent_item_id(self, item_id: str) -> str | None:
    # async def get_item_path(self, item_id: str) -> str:
    # async def get_child_item_ids(self, item_id: str) -> PagedResult[str]:

    ##
    # "tree-write" capabilities

    # async def do_move_item(self, item_id: str, new_treepath: str):
    # async def do_copy_item(self, item_id: str, new_treepath: str):

    ##
    # "version-read" capabilities

    # async def get_current_version_id(self, item_id: str) -> str:
    # async def get_version_ids(self, item_id: str) -> PagedResult[str]:

    ##
    # "version-write" capabilities

    # async def do_restore_version(self, item_id: str, version_id: str):
