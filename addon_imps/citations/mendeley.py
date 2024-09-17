import asyncio

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
        async with self.network.GET("folders") as response:
            response_json = await response.json_content()
            raw_collections = [
                collection
                for collection in response_json
                if "parent_id" not in collection
            ]
            return self._parse_collection_response(raw_collections)

    async def list_collection_items(
        self,
        collection_id: str,
        filter_items: ItemType | None = None,
    ) -> ItemSampleResult:
        async with self.network.GET(
            f"folders/{collection_id}/documents",
        ) as response:
            document_ids = await response.json_content()
            items = await self._fetch_documents_details(document_ids, filter_items)

            return ItemSampleResult(items=items, total_count=len(items))

    async def _fetch_documents_details(
        self, document_ids: list[dict], filter_items: ItemType | None
    ) -> list[ItemResult]:
        tasks = [
            self._fetch_item_details(doc["id"], filter_items) for doc in document_ids
        ]

        return list(await asyncio.gather(*tasks))

    async def _fetch_item_details(
        self,
        item_id: str,
        filter_items: ItemType | None,
    ) -> ItemResult:
        async with self.network.GET(f"documents/{item_id}") as item_response:
            item_details = await item_response.json_content()
            item_name = item_details.get("title", f"Untitled Document {item_id}")
            csl_data = _citation_for_mendeley_document(item_id, item_details)
            return ItemResult(
                item_id=item_id,
                item_name=item_name,
                item_type=ItemType.DOCUMENT,
                item_path=item_details.get("path", []),
                csl=csl_data,
            )

    def _parse_collection_response(self, response_json: dict) -> ItemSampleResult:
        items = [
            ItemResult(
                item_id=collection["id"],
                item_name=collection["name"],
                item_type=ItemType.COLLECTION,
                item_path=None,
                csl=None,
            )
            for collection in response_json
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
