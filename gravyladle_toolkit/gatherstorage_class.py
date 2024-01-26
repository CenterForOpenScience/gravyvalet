from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from addon_service.namespaces import GRAVY

from .capability import (
    immediate_capability,
    proxy_act_capability,
    proxy_read_capability,
)
from .interfaces import PagedResult


# what an example gravy:StorageInterface implementation could be like (class-based)
STORAGE_INTERFACE_NORMS = gather.GatheringNorms(
    namestory=(
        rdf.Literal("Storage interface norms", language="en"),
        rdf.Literal("Norms for an interface with a storage service", language="en"),
    ),
    focustype_iris={},
)


class StorageInterfaceOrganizer(gather.GatheringOrganizer):
    norms = STORAGE_INTERFACE_NORMS
    thesaurus = {}


class StorageInterface(BaseAddonInterface):
    ##
    # "item-read" capabilities:

    @immediate_capability(GRAVY.item_download_url, requires={GRAVY.read})
    def item_download_url(self, item_id: str) -> str:
        raise NotImplementedError  # waterbutler url, when appropriate

    @proxy_read_capability(GRAVY.get_item_description, requires={GRAVY.read})
    async def get_item_description(self, item_id: str) -> dict:
        raise NotImplementedError

    ##
    # "item-write" capabilities:

    @immediate_capability(GRAVY.item_upload_url, requires={GRAVY.write})
    def item_upload_url(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_act_capability(GRAVY.pls_delete_item, requires={GRAVY.write})
    async def pls_delete_item(self, item_id: str):
        raise NotImplementedError

    ##
    # "tree-read" capabilities:

    @proxy_read_capability(GRAVY.get_root_item_ids, requires={GRAVY.read, GRAVY.tree})
    async def get_root_item_ids(self) -> PagedResult[str]:
        raise NotImplementedError

    @proxy_read_capability(GRAVY.get_parent_item_id, requires={GRAVY.read, GRAVY.tree})
    async def get_parent_item_id(self, item_id: str) -> str | None:
        raise NotImplementedError

    @proxy_read_capability(GRAVY.get_item_path, requires={GRAVY.read, GRAVY.tree})
    async def get_item_path(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_read_capability(GRAVY.get_child_item_ids, requires={GRAVY.read, GRAVY.tree})
    async def get_child_item_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    ##
    # "tree-write" capabilities

    @proxy_act_capability(GRAVY.pls_move_item, requires={GRAVY.write, GRAVY.tree})
    async def pls_move_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    @proxy_act_capability(GRAVY.pls_copy_item, requires={GRAVY.write, GRAVY.tree})
    async def pls_copy_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    ##
    # "version-read" capabilities

    @proxy_read_capability(
        GRAVY.get_current_version_id, requires={GRAVY.read, GRAVY.version}
    )
    async def get_current_version_id(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_read_capability(GRAVY.get_version_ids, requires={GRAVY.read, GRAVY.version})
    async def get_version_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    ##
    # "version-write" capabilities

    @proxy_act_capability(
        GRAVY.pls_restore_version, requires={GRAVY.write, GRAVY.version}
    )
    async def pls_restore_version(self, item_id: str, version_id: str):
        raise NotImplementedError
