from addon_toolkit import RedirectResult
from addon_toolkit.storage import (
    ItemResult,
    ItemSampleResult,
    StorageAddon,
)


class MyBlargStorage(StorageAddon):
    """blarg?"""

    def download(self, item_id: str) -> RedirectResult:
        """blarg blarg blarg"""
        return RedirectResult(f"/{item_id}")

    async def get_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        return ItemSampleResult([ItemResult(item_id="hello", item_name="Hello!?")])
