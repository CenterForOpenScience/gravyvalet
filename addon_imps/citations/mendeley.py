import asyncio

from addon_toolkit.async_utils import join_list
from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class MendeleyCitationImp(CitationAddonImp):
    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        async with self.network.GET(
            "profiles/me",
        ) as response:
            profile_info = await response.json_content()
            user_id = profile_info.get("id")
            if not user_id:
                raise KeyError("Failed to fetch user ID from Mendeley.")
            return str(user_id)

    async def list_root_collections(self) -> ItemSampleResult:
        return ItemSampleResult(
            items=[
                ItemResult(
                    item_id="ROOT",
                    item_type=ItemType.COLLECTION,
                    item_name="All Documents",
                )
            ]
        )

    async def get_item_info(self, item_id: str):
        if item_id == "ROOT":
            return ItemResult(
                item_id="ROOT",
                item_type=ItemType.COLLECTION,
                item_name="ROOT",
            )
        item_type, parsed_id = item_id.split(":", maxsplit=1)
        if item_type == "collection":
            return await self._fetch_collection(parsed_id)
        elif item_type == "document":
            return await self._fetch_item_details(parsed_id)

    async def _fetch_collection(self, item_id: str):
        async with self.network.GET(f"folders/{item_id}") as response:
            collection = await response.json_content()
            return ItemResult(
                item_id=f'{ItemType.COLLECTION}:{collection["id"]}',
                item_name=collection["name"],
                item_type=ItemType.COLLECTION,
            )

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
    ) -> ItemSampleResult:
        parsed_id = (
            collection_id
            if collection_id == "ROOT"
            else collection_id.split(":", maxsplit=1)[1]
        )
        tasks = []
        if filter_items != ItemType.COLLECTION:
            tasks.append(self._fetch_collection_documents(parsed_id))
        if filter_items != ItemType.DOCUMENT:
            tasks.append(self._fetch_subcollections(parsed_id))
        items = await join_list(tasks)

        return ItemSampleResult(items=items, total_count=len(items))

    async def _fetch_subcollections(self, collection_id):
        async with self.network.GET(
            "folders",
        ) as response:
            document_ids = await response.json_content()
            items = self._parse_collection_response(document_ids, collection_id)

            return items.items

    async def _fetch_collection_documents(self, collection_id: str):
        if collection_id and collection_id != "ROOT":
            prefix = f"folders/{collection_id}/"
        else:
            prefix = ""
        async with self.network.GET(
            f"{prefix}documents",
        ) as response:
            document_ids = await response.json_content()
            return await self._fetch_documents_details(document_ids)

    async def _fetch_documents_details(
        self, document_ids: list[dict]
    ) -> list[ItemResult]:
        tasks = [self._fetch_item_details(doc["id"]) for doc in document_ids]

        return list(await asyncio.gather(*tasks))

    async def _fetch_item_details(
        self,
        item_id: str,
    ) -> ItemResult:
        async with self.network.GET(f"documents/{item_id}") as item_response:
            item_details = await item_response.json_content()
            item_name = item_details.get("title", f"Untitled Document {item_id}")
            csl_data = _citation_for_mendeley_document(item_id, item_details)
            return ItemResult(
                item_id=f"{ItemType.DOCUMENT}:{item_id}",
                item_name=item_name,
                item_type=ItemType.DOCUMENT,
                item_path=item_details.get("path", []),
                csl=csl_data,
            )

    def _parse_collection_response(
        self, response_json: dict, parent_id: str
    ) -> ItemSampleResult:
        items = [
            ItemResult(
                item_id=f'{ItemType.COLLECTION}:{collection["id"]}',
                item_name=collection["name"],
                item_type=ItemType.COLLECTION,
            )
            for collection in response_json
            if collection.get("parent_id", "ROOT") == parent_id
        ]

        return ItemSampleResult(items=items, total_count=len(items))


def sanitize_person(person):
    given = person.get("first_name", "").strip()
    family = person.get("last_name", "").strip()
    if given or family:
        return {"given": given if given else "", "family": family}
    return None


def _citation_for_mendeley_document(item_id, item_details):
    CSL_TYPE_MAP = {
        "book_section": "chapter",
        "case": "legal_case",
        "computer_program": "article",
        "conference_proceedings": "paper-conference",
        "encyclopedia_article": "entry-encyclopedia",
        "film": "motion_picture",
        "generic": "article",
        "hearing": "speech",
        "journal": "article-journal",
        "magazine_article": "article-magazine",
        "newspaper_article": "article-newspaper",
        "statute": "legislation",
        "television_broadcast": "broadcast",
        "web_page": "webpage",
        "working_paper": "report",
    }

    csl = {
        "id": item_id,
        "type": CSL_TYPE_MAP.get(item_details.get("type"), "article"),
        "abstract": item_details.get("abstract"),
        "accessed": item_details.get("accessed"),
        "author": (
            [
                sanitized_person
                for sanitized_person in (
                    sanitize_person(person)
                    for person in item_details.get("authors", [])
                )
                if sanitized_person is not None
            ]
            if item_details.get("authors")
            else None
        ),
        "chapter-number": item_details.get("chapter"),
        "publisher-place": ", ".join(
            filter(None, [item_details.get("city"), item_details.get("country")])
        )
        or None,
        "edition": item_details.get("edition"),
        "editor": (
            [
                sanitized_person
                for sanitized_person in (
                    sanitize_person(person)
                    for person in item_details.get("editors", [])
                )
                if sanitized_person is not None
            ]
            if item_details.get("editors")
            else None
        ),
        "genre": item_details.get("genre"),
        "issue": item_details.get("issue"),
        "language": item_details.get("language"),
        "medium": item_details.get("medium"),
        "page": item_details.get("pages"),
        "publisher": (
            item_details.get("institution")
            if item_details.get("type") == "thesis"
            else item_details.get("publisher")
        ),
        "number": item_details.get("revision"),
        "collection-title": item_details.get("series"),
        "collection-editor": item_details.get("series_editor"),
        "shortTitle": item_details.get("short_title"),
        "container-title": item_details.get("source"),
        "title": item_details.get("title"),
        "volume": item_details.get("volume"),
        "URL": item_details.get("websites", [None])[0],
        "issued": (
            {"date-parts": [[item_details.get("year")]]}
            if item_details.get("year")
            else None
        ),
    }

    idents = item_details.get("identifiers", {})
    csl.update(
        {
            "DOI": idents.get("doi"),
            "ISBN": idents.get("isbn"),
            "ISSN": idents.get("issn"),
            "PMID": idents.get("pmid"),
        }
    )

    csl = {key: value for key, value in csl.items() if value is not None}

    return csl
