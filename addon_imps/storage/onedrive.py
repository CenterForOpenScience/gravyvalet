from urllib.parse import (
    parse_qs,
    urlparse,
)

from addon_toolkit.cursor import Cursor
from addon_toolkit.interfaces import storage


class NextLinkCursor(Cursor):
    def __init__(self, next_link: str):
        self.this_cursor_str = next_link


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
                item_type=(
                    storage.ItemType.FOLDER
                    if "folder" in _json
                    else storage.ItemType.FILE
                ),
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
                    item_type=(
                        storage.ItemType.FOLDER
                        if "folder" in item
                        else storage.ItemType.FILE
                    ),
                )
                for item in _json.get("value", [])
            ]
            next_link = _json.get("@odata.nextLink", "")
            if next_link:
                cursor = NextLinkCursor(next_link)
                result = storage.ItemSampleResult(items=items).with_cursor(cursor)
            else:
                result = storage.ItemSampleResult(items=items)
            return result

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        if not cursor:
            return {}
        parsed_url = urlparse(cursor)
        query_params = parse_qs(parsed_url.query)
        flat_query_params = {k: v[0] for k, v in query_params.items()}
        return flat_query_params
