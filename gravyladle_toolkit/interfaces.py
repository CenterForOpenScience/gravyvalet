import dataclasses
from typing import (
    Awaitable,
    Callable,
)

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)


@dataclasses.dataclass
class PagedResult:  # (TODO: move to gravyvalet)
    page: list
    get_next_page: Callable[[], Awaitable["PagedResult"]]  # (TODO: cursor?)


@dataclasses.dataclass
class BaseAddonInterface:
    # attrs on `self` when your StorageInterface subclass is instantiated
    authorized_account: AuthorizedStorageAccount
    configured_addon: ConfiguredStorageAddon | None

    def invoke_immediate_capability(self, capability_iri: str, **kwargs):
        raise NotImplementedError  # TODO

    def invoke_proxy_read_capability(self, capability_iri: str, **kwargs):
        raise NotImplementedError  # TODO

    def invoke_proxy_act_capability(self, capability_iri: str, **kwargs):
        raise NotImplementedError  # TODO
