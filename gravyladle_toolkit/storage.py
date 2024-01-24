from addon_service.namespaces import GRAVY

from .interfaces import (
    BaseAddonInterface,
    PagedResult,
)


###
# ONE OPTION: use decorators to declare capability identifiers on interface methods

# something like:


def immediate_capability(*, requires):
    # decorator for capabilities that can be computed immediately,
    # without sending any requests or waiting on external resources
    # (e.g. build a url in a known pattern or return declared static metadata)
    def _decorator(fn):
        return fn  # decorator stub (TODO: register someway addon_service can use it)

    return _decorator


def proxy_read_capability(*, requires):
    # decorator for capabilities that require fetching data from elsewhere,
    # but make no changes (e.g. get metadata about an item from an external service)
    def _decorator(fn):
        return fn  # decorator stub (TODO)

    return _decorator


def proxy_act_capability(*, requires):
    # decorator for capabilities that initiate change, may take some time,
    # and may fail in strange ways (e.g. delete an item, copy a file tree)
    def _decorator(fn):
        return fn  # decorator stub (TODO)

    return _decorator


# what a base StorageInterface could be like
class StorageInterface(BaseAddonInterface):
    ##
    # "item-read" capabilities:

    @immediate_capability(requires={GRAVY.read})
    def item_download_url(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_read_capability(requires={GRAVY.read})
    async def get_item_description(self, item_id: str) -> dict:
        raise NotImplementedError

    ##
    # "item-write" capabilities:

    @immediate_capability(requires={GRAVY.write})
    def item_upload_url(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_act_capability(requires={GRAVY.write})
    async def pls_delete_item(self, item_id: str):
        raise NotImplementedError

    ##
    # "tree-read" capabilities:

    @proxy_read_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_root_item_ids(self) -> PagedResult[str]:
        raise NotImplementedError

    @proxy_read_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_child_item_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    @proxy_read_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_parent_item_id(self, item_id: str) -> str | None:
        raise NotImplementedError

    @proxy_read_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_item_path(self, item_id: str) -> str:
        raise NotImplementedError

    ##
    # "tree-write" capabilities

    @proxy_act_capability(requires={GRAVY.write, GRAVY.tree})
    async def pls_move_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    @proxy_act_capability(requires={GRAVY.write, GRAVY.tree})
    async def pls_copy_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    ##
    # "version-read" capabilities

    @proxy_read_capability(requires={GRAVY.read, GRAVY.version})
    async def get_current_version_id(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_read_capability(requires={GRAVY.read, GRAVY.version})
    async def get_version_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    ##
    # "version-write" capabilities

    @proxy_act_capability(requires={GRAVY.write, GRAVY.version})
    async def pls_restore_version(self, item_id: str, version_id: str):
        raise NotImplementedError
