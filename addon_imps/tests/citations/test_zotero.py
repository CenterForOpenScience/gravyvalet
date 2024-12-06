import unittest
from unittest.mock import (
    AsyncMock,
    create_autospec,
)

from addon_imps.citations.zotero_org import ZoteroOrgCitationImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.citation import (
    CitationConfig,
    ItemResult,
    ItemType,
)


# noinspection PyDataclass
class TestZoteroOrgCitationImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = CitationConfig(
            external_api_url="https://api.zotero.org",
            connected_root_id=None,
            external_account_id="123456",
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.zotero_imp = ZoteroOrgCitationImp(config=self.config, network=self.network)

    async def test_get_external_account_id_with_auth_extras(self):
        auth_result_extras = {"userID": "user-123"}
        result = await self.zotero_imp.get_external_account_id(auth_result_extras)
        self.assertEqual(result, "user-123")

    async def test_get_external_account_id_without_auth_extras(self):
        auth_result_extras = {}
        mock_response = {"userID": "user-456"}
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.status = 200
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = await self.zotero_imp.get_external_account_id(auth_result_extras)

        self.assertEqual(result, "user-456")
        self.zotero_imp.network.GET.assert_called_with("keys")

    async def test_list_root_collections(self):
        mock_response = [
            {"id": "collection-1", "data": {"name": "Collection 1"}},
            {"id": "collection-2", "data": {"name": "Collection 2"}},
        ]
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        result = await self.zotero_imp.list_root_collections()

        expected_items = [
            ItemResult(
                item_id="collection-1:",
                item_name="Collection 1",
                item_type=ItemType.COLLECTION,
            ),
            ItemResult(
                item_id="collection-2:",
                item_name="Collection 2",
                item_type=ItemType.COLLECTION,
            ),
            ItemResult(
                item_id="personal:",
                item_name="My Library",
                item_type=ItemType.COLLECTION,
            ),
        ]

        self.assertEqual(result.items, expected_items)
        self.zotero_imp.network.GET.assert_called_with(
            f"users/{self.config.external_account_id}/groups"
        )

    async def test_list_collection_items(self):
        collections = [
            ItemResult(
                item_id="collection-1:",
                item_name="Collection Title 1",
                item_type=ItemType.DOCUMENT,
            ),
            ItemResult(
                item_id="collection-2",
                item_name="Collection Title 2",
                item_type=ItemType.DOCUMENT,
            ),
        ]

        docs = [
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
        self.zotero_imp.fetch_collection_documents = create_autospec(
            self.zotero_imp.fetch_collection_documents, return_value=docs
        )
        self.zotero_imp.fetch_subcollections = create_autospec(
            self.zotero_imp.fetch_subcollections, return_value=collections
        )
        result = await self.zotero_imp.list_collection_items("personal:collection-123")

        expected_items = docs + collections
        self.zotero_imp.fetch_collection_documents.assert_awaited_once_with(
            "personal", "collection-123"
        )
        self.zotero_imp.fetch_subcollections.assert_awaited_once_with(
            "personal", "collection-123"
        )
        self.assertEqual(result.items, expected_items)
        self.zotero_imp.network.GET.assert_not_called()

    async def test_list_collection_items_with_filter(self):
        return_items = [
            ItemResult(
                item_id="item-1",
                item_name="Item Title 1",
                item_type=ItemType.COLLECTION,
            ),
            ItemResult(
                item_id="item-2",
                item_name="Item Title 2",
                item_type=ItemType.COLLECTION,
            ),
        ]
        self.zotero_imp.fetch_collection_documents = create_autospec(
            self.zotero_imp.fetch_collection_documents,
            return_value=return_items,
        )
        self.zotero_imp.fetch_subcollections = create_autospec(
            self.zotero_imp.fetch_subcollections,
            return_value=return_items,
        )
        cases = [
            [
                ItemType.COLLECTION,
                self.zotero_imp.fetch_subcollections,
                self.zotero_imp.fetch_collection_documents,
            ],
            [
                ItemType.DOCUMENT,
                self.zotero_imp.fetch_collection_documents,
                self.zotero_imp.fetch_subcollections,
            ],
        ]
        for item_type, call, not_call in cases:
            with self.subTest(item_type):
                result = await self.zotero_imp.list_collection_items(
                    "personal:collection-123", filter_items=item_type
                )
                call.assert_awaited_once_with("personal", "collection-123")
                not_call.assert_not_called()
                self.assertEqual(result.items, return_items)
                self.zotero_imp.network.GET.assert_not_called()
            call.reset_mock()
            not_call.reset_mock()

    async def test_fetch_collection_documents(self):
        mock_response = {
            "items": [
                {"id": "item-1", "title": "Item Title 1"},
                {"id": "item-2", "title": "Item Title 2"},
            ]
        }
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )
        self.zotero_imp.resolve_collection_prefix = create_autospec(
            self.zotero_imp.resolve_collection_prefix, return_value="la"
        )
        expected_result = [
            ItemResult(
                item_id="personal:item-1",
                item_name="Item Title 1",
                item_type=ItemType.DOCUMENT,
                csl={"id": "item-1", "title": "Item Title 1"},
            ),
            ItemResult(
                item_id="personal:item-2",
                item_name="Item Title 2",
                item_type=ItemType.DOCUMENT,
                csl={"id": "item-2", "title": "Item Title 2"},
            ),
        ]
        result = await self.zotero_imp.fetch_collection_documents(
            "personal", "collection"
        )

        self.assertEqual(result, expected_result)
        self.zotero_imp.network.GET.assert_called_once_with(
            "la/items/top", query={"format": "csljson"}
        )

    async def test_fetch_subcollections(self):
        mock_response = [
            {"key": "collection-1", "data": {"name": "Collection 1"}},
            {"key": "collection-2", "data": {"name": "Collection 2"}},
        ]
        self.zotero_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )
        self.zotero_imp.resolve_collection_prefix = create_autospec(
            self.zotero_imp.resolve_collection_prefix, return_value="la"
        )
        expected_result = [
            ItemResult(
                item_id="personal:collection-1",
                item_name="Collection 1",
                item_type=ItemType.COLLECTION,
            ),
            ItemResult(
                item_id="personal:collection-2",
                item_name="Collection 2",
                item_type=ItemType.COLLECTION,
            ),
        ]
        result = await self.zotero_imp.fetch_subcollections("personal", "collection")

        self.assertEqual(result, expected_result)
        self.zotero_imp.network.GET.assert_called_once_with("la/collections/top")
