from addon_toolkit import storage


class BoxDotComStorage(storage.StorageAddon):
    """storage on box.com"""

    async def get_root_item_ids(self, page_cursor: str = "") -> storage.ManyItemResult:
        return storage.ManyItemResult(
            item_ids=["2"],
        )
