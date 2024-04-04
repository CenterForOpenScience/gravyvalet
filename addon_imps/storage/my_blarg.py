from addon_toolkit import RedirectResult
from addon_toolkit.storage import (
    ItemArg,
    PageArg,
    PagedResult,
    StorageAddonProtocol,
)


class MyBlargStorage(StorageAddonProtocol):
    """blarg?"""

    def download(self, item: ItemArg) -> RedirectResult:
        """blarg blarg blarg"""
        return RedirectResult(f"http://blarg.example/{item.item_id}")

    def blargblarg(self, item: ItemArg) -> PagedResult:
        return PagedResult(["hello"])

    def opop(self, item: ItemArg, page: PageArg) -> PagedResult:
        return PagedResult(["hello"])
