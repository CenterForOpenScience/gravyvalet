import unittest
from unittest.mock import (
    AsyncMock,
    create_autospec,
    sentinel,
)

from addon_imps.citations.mendeley import MendeleyCitationImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.citation import (
    CitationConfig,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class TestMendeleyCitationImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = CitationConfig(
            external_api_url="https://api.mendeley.com",
            connected_root_id=None,
            external_account_id=None,
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.mendeley_imp = MendeleyCitationImp(
            config=self.config, network=self.network
        )

    async def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self.mendeley_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = await self.mendeley_imp.get_external_account_id({})

        self.assertEqual(result, "12345")
        self.mendeley_imp.network.GET.assert_called_with("profiles/me")

    async def test_list_root_collections(self):
        mock_response_data = [
            {"id": "1", "name": "Collection 1"},
            {"id": "2", "name": "Collection 2"},
        ]
        self.mendeley_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response_data
        )

        result = await self.mendeley_imp.list_root_collections()

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="ROOT",
                    item_name="All Documents",
                    item_type=ItemType.COLLECTION,
                ),
            ],
            total_count=2,
        )

        self.assertEqual(
            sorted(result.items, key=lambda x: x.item_id),
            sorted(expected_result.items, key=lambda x: x.item_id),
        )
        self.mendeley_imp.network.GET.assert_not_called()

    async def test_fetch_collection_documents(self):
        mock_document_ids = [{"id": "doc1"}, {"id": "doc2"}]
        mock_doc1_details = {
            "id": "doc1",
            "title": "Doc Title 1",
            "type": "journal",
            "authors": [{"first_name": "John", "last_name": "Doe"}],
            "path": [],
        }
        mock_doc2_details = {
            "id": "doc2",
            "title": "Doc Title 2",
            "type": "book_section",
            "path": [],
        }

        self.mendeley_imp.network.GET.side_effect = [
            AsyncMock(
                __aenter__=AsyncMock(
                    return_value=AsyncMock(
                        json_content=AsyncMock(return_value=mock_document_ids)
                    )
                )
            ),
            AsyncMock(
                __aenter__=AsyncMock(
                    return_value=AsyncMock(
                        json_content=AsyncMock(return_value=mock_doc1_details)
                    )
                )
            ),
            AsyncMock(
                __aenter__=AsyncMock(
                    return_value=AsyncMock(
                        json_content=AsyncMock(return_value=mock_doc2_details)
                    )
                )
            ),
        ]

        result = await self.mendeley_imp._fetch_collection_documents("folder_id")

        expected_items = [
            ItemResult(
                item_id="doc1",
                item_name="Doc Title 1",
                item_type=ItemType.DOCUMENT,
                item_path=[],
                csl={
                    "id": "doc1",
                    "type": "article-journal",
                    "author": [{"given": "John", "family": "Doe"}],
                    "title": "Doc Title 1",
                },
            ),
            ItemResult(
                item_id="doc2",
                item_name="Doc Title 2",
                item_type=ItemType.DOCUMENT,
                item_path=[],
                csl={"id": "doc2", "type": "chapter", "title": "Doc Title 2"},
            ),
        ]

        self.assertEqual(
            sorted(result, key=lambda x: x.item_id),
            sorted(expected_items, key=lambda x: x.item_id),
        )

    async def test_fetch_subcollections(self):
        mock_response_data = [
            {"id": "1", "name": "Collection 1", "parent_id": "collection_id"},
            {"id": "2", "name": "Collection 2", "parent_id": "collection_id"},
            {"id": "3", "name": "Collection 3"},
        ]
        self.mendeley_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response_data
        )

        result = await self.mendeley_imp._fetch_subcollections("collection_id")

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="1", item_name="Collection 1", item_type=ItemType.COLLECTION
                ),
                ItemResult(
                    item_id="2", item_name="Collection 2", item_type=ItemType.COLLECTION
                ),
            ],
            total_count=2,
        )

        self.assertEqual(
            sorted(result, key=lambda x: x.item_id),
            sorted(expected_result.items, key=lambda x: x.item_id),
        )
        self.mendeley_imp.network.GET.assert_called_once_with("folders")

    async def test_list_collection_items(self):
        collections = [sentinel.collection1, sentinel.collection2]
        documents = [sentinel.document1, sentinel.document2]
        self.mendeley_imp._fetch_subcollections = create_autospec(
            self.mendeley_imp._fetch_subcollections, return_value=collections
        )
        self.mendeley_imp._fetch_collection_documents = create_autospec(
            self.mendeley_imp._fetch_collection_documents, return_value=documents
        )
        cases = [
            [
                ItemType.COLLECTION,
                [self.mendeley_imp._fetch_subcollections],
                [self.mendeley_imp._fetch_collection_documents],
                ItemSampleResult(collections, total_count=2),
            ],
            [
                None,
                [
                    self.mendeley_imp._fetch_subcollections,
                    self.mendeley_imp._fetch_collection_documents,
                ],
                [],
                ItemSampleResult(documents + collections, total_count=4),
            ],
            [
                ItemType.DOCUMENT,
                [self.mendeley_imp._fetch_collection_documents],
                [self.mendeley_imp._fetch_subcollections],
                ItemSampleResult(documents, total_count=2),
            ],
        ]
        for (
            item_filter,
            calls_to_be_made,
            calls_not_to_be_made,
            expected_result,
        ) in cases:
            with self.subTest(item_filter):
                result = await self.mendeley_imp.list_collection_items(
                    "collection_id", filter_items=item_filter
                )
                for call in calls_to_be_made:
                    call.assert_awaited_once_with("collection_id")
                for call in calls_not_to_be_made:
                    call.assert_not_called()
                self.assertEqual(result, expected_result)
            self.mendeley_imp._fetch_subcollections.reset_mock()
            self.mendeley_imp._fetch_collection_documents.reset_mock()
