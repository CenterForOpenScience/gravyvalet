import dataclasses
from typing import Awaitable, Callable

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)


@dataclasses.dataclass
class PagedResult:  # (TODO: move to gravyvalet)
    page: list
    get_next_page: Callable[[], Awaitable['PagedResult']]  # (TODO: cursor?)


@dataclasses.dataclass
class BaseAddonInterface:
    # attrs on `self` when your StorageInterface subclass is instantiated
    authorized_account: AuthorizedStorageAccount
    configured_addon: ConfiguredStorageAddon
