from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class MendeleyCitationImp(CitationAddonImp):
    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        return auth_result_extras["userID"]

    async def list_root_collections(self) -> ItemSampleResult:
        async with self.network.GET(
            f"{self.config.external_api_url}/folders"
        ) as response:
            response_json = await response.json_content()
            return self._parse_collection_response(response_json)

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
        page_cursor: str = "",
    ) -> ItemSampleResult:
        async with self.network.GET(
            f"{self.config.external_api_url}/folders/{collection_id}/documents",
            query=self._params_from_cursor(page_cursor),
        ) as response:
            response_json = await response.json_content()
            return self._parse_items_response(response_json, filter_items)

    # async def add_new_item(self, collection_id: str, item_data: dict) -> ItemResult:
    #     async with self.network.POST(f"{self.config.external_api_url}/folders/{collection_id}/documents", json=item_data) as response:
    #         new_item = await response.json_content()
    #         return ItemResult(
    #             item_id=int(new_item['id']),
    #             item_name=new_item['title'],
    #             item_type=ItemType.DOCUMENT,
    #             csl=new_item.get("csl", {})
    #         )
    #
    # async def delete_item(self, item_id: str) -> None:
    #     async with self.network.DELETE(f"{self.config.external_api_url}/documents/{item_id}") as response:
    #         if response.status_code != 204:
    #             raise Exception("Failed to delete item")

    def _parse_collection_response(self, response_json: dict) -> ItemSampleResult:
        items = [
            ItemResult(
                item_id=int(collection["id"]),
                item_name=collection["name"],
                item_type=ItemType.COLLECTION,
                item_path=None,
                csl=None,
            )
            for collection in response_json.get("folders", [])
        ]
        return ItemSampleResult(items=items, total_count=len(items))

    def _parse_items_response(
        self, response_json: dict, filter_items: ItemType | None
    ) -> ItemSampleResult:
        items = [
            ItemResult(
                item_id=int(item["id"]),
                item_name=item["title"],
                item_type=(
                    ItemType.DOCUMENT
                    if item["type"] == "document"
                    else ItemType.COLLECTION
                ),
                item_path=None,
                csl=item.get("csl", {}),
            )
            for item in response_json.get("documents", [])
            if filter_items is None
            or (filter_items == ItemType.DOCUMENT and item["type"] == "document")
        ]
        return ItemSampleResult(items=items, total_count=len(items))

    # def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
    #     if cursor:
    #         offset_cursor = OffsetCursor.from_str(cursor)
    #         return {"start": offset_cursor.offset, "limit": offset_cursor.limit}
    #     return {}
    #
    # def _parse_cursor(self, headers: dict[str, str]) -> OffsetCursor:
    #     total_count = int(headers.get('Total-Results', 0))
    #     offset = int(headers.get('Start', 0))
    #     limit = int(headers.get('Items-Per-Page', 50))
    #     return OffsetCursor(offset=offset, limit=limit, total_count=total_count)
    #
    # @functools.cache
    # def _root_collection_id(self) -> str:
    #     return "root"
    #
    #
    # m = MendeleyCitationImp()
