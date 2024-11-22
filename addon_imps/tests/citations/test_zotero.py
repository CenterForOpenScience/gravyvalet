import asyncio
import unittest
from unittest.mock import AsyncMock

from addon_imps.citations.zotero_org import ZoteroOrgCitationImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.citation import (
    CitationConfig,
    ItemResult,
    ItemType,
)


class TestZoteroOrgCitationImp(unittest.TestCase):

    def setUp(self):
        self.config = CitationConfig(
            external_api_url="https://api.zotero.org",
            connected_root_id=None,
            external_account_id="123456",
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.zotero_imp = ZoteroOrgCitationImp(config=self.config, network=self.network)

    def test_get_external_account_id_with_auth_extras(self):
        auth_result_extras = {"userID": "user-123"}
        result = asyncio.run(
            self.zotero_imp.get_external_account_id(auth_result_extras)
        )
        self.assertEqual(result, "user-123")

    def test_get_external_account_id_without_auth_extras(self):
        auth_result_extras = {}
        mock_response = {"userID": "user-456"}
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.status = 200
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = asyncio.run(
            self.zotero_imp.get_external_account_id(auth_result_extras)
        )
        self.assertEqual(result, "user-456")
        self.zotero_imp.network.GET.assert_called_with("keys")

    def test_list_root_collections(self):
        mock_response = [
            {"key": "collection-1", "data": {"name": "Collection 1"}},
            {"key": "collection-2", "data": {"name": "Collection 2"}},
        ]
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = asyncio.run(self.zotero_imp.list_root_collections())

        expected_items = [
            ItemResult(
                item_id="collection-1",
                item_name="Collection 1",
                item_type=ItemType.COLLECTION,
            ),
            ItemResult(
                item_id="collection-2",
                item_name="Collection 2",
                item_type=ItemType.COLLECTION,
            ),
        ]

        self.assertEqual(result.items, expected_items)
        self.assertEqual(result.total_count, 2)
        self.zotero_imp.network.GET.assert_called_with(
            f"users/{self.config.external_account_id}/collections"
        )

    def test_list_collection_items(self):
        mock_response = [
            {"key": "item-1", "data": {"title": "Item Title 1"}},
            {"key": "item-2", "data": {"title": "Item Title 2"}},
        ]
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = asyncio.run(self.zotero_imp.list_collection_items("collection-123"))

        expected_items = [
            ItemResult(
                item_id="item-1",
                item_name="Item Title 1",
                item_type=ItemType.DOCUMENT,
            ),
            ItemResult(
                item_id="item-2",
                item_name="Item Title 2",
                item_type=ItemType.DOCUMENT,
            ),
        ]

        self.assertEqual(result.items, expected_items)
        self.assertEqual(result.total_count, 2)
        self.zotero_imp.network.GET.assert_called_with(
            f"users/{self.config.external_account_id}/collections/collection-123/items"
        )
