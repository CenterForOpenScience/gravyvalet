import asyncio
import unittest
from unittest.mock import AsyncMock

from addon_imps.citations.mendeley import MendeleyCitationImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.citation import (
    CitationConfig,
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class TestMendeleyCitationImp(unittest.TestCase):

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

    def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self.mendeley_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = asyncio.run(self.mendeley_imp.get_external_account_id({}))

        self.assertEqual(result, "12345")
        self.mendeley_imp.network.GET.assert_called_with("profiles/me")

    def test_list_root_collections(self):
        mock_response_data = [
            {"id": "1", "name": "Collection 1"},
            {"id": "2", "name": "Collection 2"},
        ]
        self.mendeley_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response_data
        )

        result = asyncio.run(self.mendeley_imp.list_root_collections())

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
            sorted(result.items, key=lambda x: x.item_id),
            sorted(expected_result.items, key=lambda x: x.item_id),
        )
        self.mendeley_imp.network.GET.assert_called_with("folders")

    def test_list_collection_items(self):
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

        result = asyncio.run(self.mendeley_imp.list_collection_items("folder_id"))

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
            sorted(result.items, key=lambda x: x.item_id),
            sorted(expected_items, key=lambda x: x.item_id),
        )
