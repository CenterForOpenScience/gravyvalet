from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class ZoteroOrgCitationImp(CitationAddonImp):

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        user_id = auth_result_extras.get("userID")
        if user_id:
            return user_id
        async with self.network.GET(
            "keys",
        ) as response:
            if response.status == 200:
                key_info = await response.json_content()
                user_id = key_info.get("userID")
                if not user_id:
                    raise KeyError("Failed to fetch user ID from Zotero.")
                return str(user_id)
            elif response.status == 400:
                error_message = await response.json_content().get(
                    "message", "Bad request."
                )
                raise ValueError(f"Zotero API returned 400: {error_message}")

            elif response.status == 403:
                error_message = await response.json_content().get(
                    "message", "Access forbidden."
                )
                raise PermissionError(f"Zotero API returned 403: {error_message}")

            elif response.status == 404:
                error_message = await response.json_content().get(
                    "message", "Resource not found."
                )
                raise LookupError(f"Zotero API returned 404: {error_message}")

            else:
                error_message = await response.json_content().get(
                    "message", "Unknown error occurred."
                )
                raise ValueError(
                    f"Failed to fetch key information. Status code: {response.status}, {error_message}"
                )

    async def list_root_collections(self) -> ItemSampleResult:
        async with self.network.GET(
            f"users/{self.config.external_account_id}/collections"
        ) as response:
            collections = await response.json_content()
            items = [
                ItemResult(
                    item_id=collection["key"],
                    item_name=collection["data"].get("name", "Unnamed Collection"),
                    item_type=ItemType.COLLECTION,
                )
                for collection in collections
            ]
            return ItemSampleResult(items=items, total_count=len(items))

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
    ) -> ItemSampleResult:
        async with self.network.GET(
            f"users/{self.config.external_account_id}/collections/{collection_id}/items",
        ) as response:
            items_json = await response.json_content()
            items = [
                ItemResult(
                    item_id=item["key"],
                    item_name=item["data"].get("title", "Unnamed title"),
                    item_type=ItemType.DOCUMENT,
                )
                for item in items_json
                if filter_items is None
            ]
            return ItemSampleResult(items=items, total_count=len(items))
