import dataclasses

from addon_service.namespaces import GRAVY
from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)
from .capabilities import (
    immediate_capability,
    proxy_capability,
    redirect_capability,
    action_capability,
)
from .interfaces import (
    BaseAddonInterface,
    PagedResult,
)


@dataclasses.dataclass
class StorageInterface(BaseAddonInterface):
    # attrs on `self` when your StorageInterface subclass is instantiated
    authorized_account: AuthorizedStorageAccount
    configured_addon: ConfiguredStorageAddon

    ##
    # "read" capabilities:

    @immediate_capability(requires={GRAVY.read})
    def item_download_url(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_capability(requires={GRAVY.read})
    async def get_item_description(self, item_id: str) -> dict:
        raise NotImplementedError

    ##
    # "write" capabilities:

    @redirect_capability(requires={GRAVY.write})
    def item_upload_url(self, item_id: str) -> str:
        raise NotImplementedError

    @action_capability(requires={GRAVY.write})
    async def do_delete_item(self, item_id: str):
        raise NotImplementedError

    ##
    # "tree-read" capabilities:

    @proxy_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_root_item_ids(self) -> PagedResult[str]:
        raise NotImplementedError

    @proxy_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_parent_item_id(self, item_id: str) -> str | None:
        raise NotImplementedError

    @proxy_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_item_path(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_capability(requires={GRAVY.read, GRAVY.tree})
    async def get_child_item_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    ##
    # "tree-write" capabilities

    @action_capability(requires={GRAVY.write, GRAVY.tree})
    async def do_move_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    @action_capability(requires={GRAVY.write, GRAVY.tree})
    async def do_copy_item(self, item_id: str, new_treepath: str):
        raise NotImplementedError

    ##
    # "version-read" capabilities

    @proxy_capability(requires={GRAVY.read, GRAVY.version})
    async def get_current_version_id(self, item_id: str) -> str:
        raise NotImplementedError

    @proxy_capability(requires={GRAVY.read, GRAVY.version})
    async def get_version_ids(self, item_id: str) -> PagedResult[str]:
        raise NotImplementedError

    ##
    # "version-write" capabilities

    @action_capability(requires={GRAVY.write, GRAVY.version})
    async def do_restore_version(self, item_id: str, version_id: str):
        raise NotImplementedError
