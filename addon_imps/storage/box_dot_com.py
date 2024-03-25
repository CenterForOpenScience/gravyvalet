from addon_toolkit import (
    RedirectResult,
    storage,
)


class BoxDotComStorage(storage.StorageAddon):
    """storage on box.com"""

    def download(self, item_id: str) -> RedirectResult:
        """blarg blarg blarg"""
        return RedirectResult(f"http://blarg.example/{item_id}")
