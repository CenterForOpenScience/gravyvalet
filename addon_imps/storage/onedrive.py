from addon_toolkit.cursor import OffsetCursor
from addon_toolkit.interfaces import storage


class OneDriveStorageImp(storage.StorageAddonHttpRequestorImp):
    """Storage on OneDrive

    See https://learn.microsoft.com/en-us/graph/api/resources/onedrive?view=graph-rest-1.0
    """

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        async with self.network.GET("me") as _response:
            _json = await _response.json_content()
            return str(_json["id"])

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        root_item = await self.get_item_info("root")
        return storage.ItemSampleResult(
            items=[root_item],
            total_count=1,
        )

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        async with self.network.GET(
            f"me/drive/items/{item_id}",
            query={"select": "id,name,folder,createdDateTime,lastModifiedDateTime"},
        ) as _response:
            _json = await _response.json_content()
            return storage.ItemResult(
                item_id=_json.get("id"),
                item_name=_json.get("name"),
                item_type="folder" if "folder" in _json else "file",
            )

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        async with self.network.GET(
            f"me/drive/items/{item_id}/children",
            query={
                "select": "id,name,folder,createdDateTime,lastModifiedDateTime",
                **self._params_from_cursor(page_cursor),
            },
        ) as _response:
            _json = await _response.json_content()
            items = [
                storage.ItemResult(
                    item_id=item.get("id"),
                    item_name=item.get("name"),
                    item_type="folder" if "folder" in item else "file",
                )
                for item in _json.get("value", [])
            ]
            next_link = _json.get("@odata.nextLink", "")
            return storage.ItemSampleResult(
                items=items,
            ).with_cursor(next_link if next_link else "")

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        # OneDrive uses skip and top for pagination
        try:
            _cursor = OffsetCursor.from_str(cursor)
            return {"$skip": _cursor.offset, "$top": _cursor.limit}
        except ValueError:
            return {}
