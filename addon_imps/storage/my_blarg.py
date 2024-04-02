from addon_toolkit import RedirectResult
from addon_toolkit.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageAddonImp,
)


class MyBlargStorage(StorageAddonImp):
    """blarg?"""

    def download(self, item_id: str) -> RedirectResult:
        """blarg blarg blarg"""
        return RedirectResult(f"/{item_id}")

    async def get_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        return ItemSampleResult(
            items=[
                ItemResult(
                    item_id="hello", item_name="Hello!?", item_type=ItemType.FOLDER
                )
            ],
            total_count=1,
        )
