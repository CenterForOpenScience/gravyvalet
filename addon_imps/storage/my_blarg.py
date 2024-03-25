from addon_toolkit import RedirectResult
from addon_toolkit.storage import (
    ItemArg,
    PageArg,
    PagedResult,
    StorageAddon,
)


class MyBlargStorage(StorageAddon):
    """blarg?"""

    def download(self, item: ItemArg) -> RedirectResult:
        """blarg blarg blarg"""
        return RedirectResult(relative_uri=f"/{item.item_id}")

    def blargblarg(self, item: ItemArg) -> PagedResult:
        return PagedResult(["hello"])

    def opop(self, item: ItemArg, page: PageArg) -> PagedResult:
        return PagedResult(["hello"])
