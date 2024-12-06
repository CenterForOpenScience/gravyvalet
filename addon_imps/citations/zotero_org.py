from addon_toolkit.async_utils import join_list
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
        """
        For Zotero this API call lists all libraries which user may access
        """
        async with self.network.GET(
            f"users/{self.config.external_account_id}/groups"
        ) as response:
            collections = await response.json_content()
            items = [
                ItemResult(
                    item_id=f'{collection["id"]}:',
                    item_name=collection["data"].get("name", "Unnamed Library"),
                    item_type=ItemType.COLLECTION,
                )
                for collection in collections
            ]
            items.append(
                ItemResult(
                    item_id="personal:",
                    item_name="My Library",
                    item_type=ItemType.COLLECTION,
                )
            )
            return ItemSampleResult(items=items, total_count=len(items))

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
    ) -> ItemSampleResult:
        library, collection = collection_id.split(":")
        tasks = []
        if filter_items != ItemType.COLLECTION:
            tasks.append(self.fetch_collection_documents(library, collection))
        if filter_items != ItemType.DOCUMENT:
            tasks.append(self.fetch_subcollections(library, collection))
        all_items = await join_list(tasks)
        return ItemSampleResult(items=all_items, total_count=len(all_items))

    async def fetch_subcollections(self, library, collection):
        prefix = self.resolve_collection_prefix(library, collection)
        async with self.network.GET(f"{prefix}/collections/top") as response:
            items_json = await response.json_content()
            return [
                ItemResult(
                    item_id=f'{library}:{item["key"]}',
                    item_name=item["data"].get("name", "Unnamed title"),
                    item_type=ItemType.COLLECTION,
                )
                for item in items_json
            ]

    async def fetch_collection_documents(self, library, collection):
        prefix = self.resolve_collection_prefix(library, collection)
        async with self.network.GET(
            f"{prefix}/items/top", query={"format": "csljson"}
        ) as response:
            items_json = await response.json_content()
            return [
                ItemResult(
                    item_id=f'{library}:{item["id"]}',
                    item_name=item.get("title", "Unnamed title"),
                    item_type=ItemType.DOCUMENT,
                    csl=item,
                )
                for item in items_json["items"]
            ]

    def resolve_collection_prefix(self, library: str, collection):
        if library == "personal":
            prefix = f"users/{self.config.external_account_id}"
        else:
            prefix = f"groups/{library}"
        if collection != "ROOT":
            prefix = f"{prefix}/collections/{collection}"
        return prefix
