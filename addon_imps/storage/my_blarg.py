from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageAddonHttpRequestorImp,
)


class MyBlargStorage(StorageAddonHttpRequestorImp):
    """blarg?"""

    def get_item_info(self, item_id: str) -> ItemResult:
        """blarg blarg blarg"""
        return ItemResult(
            item_id=item_id, item_name=f"item{item_id}!", item_type=ItemType.FILE
        )

    async def list_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        return ItemSampleResult(
            items=[
                ItemResult(
                    item_id="hello", item_name="Hello!?", item_type=ItemType.FOLDER
                )
            ],
            total_count=1,
        )
