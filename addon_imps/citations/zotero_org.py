from addon_toolkit.async_utils import join_list
from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


ROOT_ITEM_ID = "ROOT"

# Accounting for some post-migration artifacts
ROOT_ITEM_IDS = "ROOT", "None"


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
                    item_id=f'{ItemType.COLLECTION}:{collection["id"]}:{ROOT_ITEM_ID}',
                    item_name=collection["data"].get("name", "Unnamed Library"),
                    item_type=ItemType.COLLECTION,
                )
                for collection in collections
            ]
            items.append(
                ItemResult(
                    item_id=f"{ItemType.COLLECTION}:personal:{ROOT_ITEM_ID}",
                    item_name="My Library",
                    item_type=ItemType.COLLECTION,
                )
            )
            return ItemSampleResult(items=items, total_count=len(items))

    async def get_item_info(self, item_id: str) -> ItemResult:
        item_type, library, id_ = item_id.split(":")
        if item_type == ItemType.COLLECTION and id_ in ROOT_ITEM_IDS:
            return await self._fetch_library(library)
        if item_type == ItemType.COLLECTION:
            return await self._fetch_collection(library, id_)
        elif item_type == ItemType.DOCUMENT:
            return await self._fetch_document(library, id_)

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
    ) -> ItemSampleResult:
        _, library, collection = collection_id.split(":")
        tasks = []
        if filter_items != ItemType.COLLECTION:
            tasks.append(self.fetch_collection_documents(library, collection))
        if filter_items != ItemType.DOCUMENT:
            tasks.append(self.fetch_subcollections(library, collection))
        all_items = await join_list(tasks)
        return ItemSampleResult(items=all_items, total_count=len(all_items))

    async def fetch_subcollections(self, library, collection):
        prefix = f"{self.resolve_collection_prefix(library, collection)}/collections"
        if collection == "ROOT":
            prefix = f"{prefix}/top"
        async with self.network.GET(prefix) as response:
            items_json = await response.json_content()
            return [self._parse_collection(item, library) for item in items_json]

    @staticmethod
    def _parse_collection(item: dict, library: str) -> ItemResult:
        return ItemResult(
            item_id=f'{ItemType.COLLECTION}:{library}:{item["key"]}',
            item_name=item["data"].get("name", "Unnamed title"),
            item_type=ItemType.COLLECTION,
        )

    async def fetch_collection_documents(self, library, collection):
        prefix = self.resolve_collection_prefix(library, collection)
        async with self.network.GET(
            f"{prefix}/items/top", query={"format": "csljson"}
        ) as response:
            items_json = await response.json_content()
            return [self._parse_document(item, library) for item in items_json["items"]]

    @staticmethod
    def _parse_document(item: dict, library: str) -> ItemResult:
        return ItemResult(
            item_id=f'{ItemType.DOCUMENT}:{library}:{item["id"]}',
            item_name=item.get("title", "Unnamed title"),
            item_type=ItemType.DOCUMENT,
            csl=item,
        )

    def resolve_collection_prefix(self, library: str, collection="ROOT"):
        if library == "personal":
            prefix = f"users/{self.config.external_account_id}"
        else:
            prefix = f"groups/{library}"
        if collection != "ROOT":
            prefix = f"{prefix}/collections/{collection}"
        return prefix

    async def _fetch_collection(self, library: str, collection_id: str) -> ItemResult:
        prefix = self.resolve_collection_prefix(library, collection_id)
        async with self.network.GET(prefix) as response:
            raw_collection = await response.json_content()
            return self._parse_collection(raw_collection, library)

    async def _fetch_document(self, library: str, document_id: str) -> ItemResult:
        prefix = self.resolve_collection_prefix(library)
        async with self.network.GET(
            f"{prefix}/items/{document_id}", query={"format": "csljson"}
        ) as response:
            raw_collection = await response.json_content()
            return self._parse_document(raw_collection, library)

    async def _fetch_library(self, library: str) -> ItemResult:
        if library == "personal":
            return ItemResult(
                item_id=f"{ItemType.COLLECTION}:personal:{ROOT_ITEM_ID}",
                item_name="My Library",
                item_type=ItemType.COLLECTION,
            )
        else:
            root_collections = await self.list_root_collections()
            for collection in root_collections.items:
                if library in collection.item_id:
                    return collection
