from addon_service.namespaces import GRAVY

from .capability import (
    immediate_capability,
    proxy_act_capability,
    proxy_read_capability,
)
from .interfaces import (
    BaseAddonInterface,
    PagedResult,
)


# what a base StorageInterface could be like
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


if __debug__:  # examples

    class _ExampleStorageImplementation(StorageInterface):
        def item_download_url(self, item_id: str) -> str:
            return self._waterbutler_download_url(item_id)

        async def get_item_description(self, item_id: str) -> dict:
            return item_id  # stub

        def item_upload_url(self, item_id: str) -> str:
            return self._waterbutler_upload_url(item_id)

        async def pls_delete_item(self, item_id: str):
            raise NotImplementedError

        def _waterbutler_download_url(self, item_id):
            raise NotImplementedError

        def _waterbutler_upload_url(self, item_id):
            raise NotImplementedError
