import asyncio
import unittest
from unittest.mock import (
    AsyncMock,
    patch,
)

from addon_imps.storage.onedrive import OneDriveStorageImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.cursor import Cursor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class NextLinkCursor(Cursor):
    def __init__(self, next_link: str):
        super().__init__(cursor_str=next_link)


class TestOneDriveStorageImp(unittest.TestCase):

    def setUp(self):
        self.config = StorageConfig(
            external_api_url="https://graph.microsoft.com/v1.0",
            connected_root_id=None,
            external_account_id=None,
            max_upload_mb=100,
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.onedrive_imp = OneDriveStorageImp(config=self.config, network=self.network)

    def test_get_external_account_id(self):
        mock_response = {"id": "user-id"}
        self.onedrive_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )
        result = asyncio.run(self.onedrive_imp.get_external_account_id({}))
        self.assertEqual(result, "user-id")
        self.onedrive_imp.network.GET.assert_called_with("me")

    def test_list_root_items(self):
        mock_root_item = ItemResult(
            item_id="root-id",
            item_name="Root",
            item_type=ItemType.FOLDER,
        )
        self.onedrive_imp.get_item_info = AsyncMock(return_value=mock_root_item)
        result = asyncio.run(self.onedrive_imp.list_root_items())
        expected_result = ItemSampleResult(
            items=[mock_root_item],
            total_count=1,
        )
        self.assertEqual(result.items, expected_result.items)
        self.onedrive_imp.get_item_info.assert_called_with("root")

    def test_get_item_info(self):
        mock_response = {
            "id": "item-id",
            "name": "Item Name",
            "folder": {},
            "createdDateTime": "2021-01-01T00:00:00Z",
            "lastModifiedDateTime": "2021-01-01T00:00:00Z",
        }
        self.onedrive_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )
        result = asyncio.run(self.onedrive_imp.get_item_info("item-id"))
        expected_result = ItemResult(
            item_id="item-id",
            item_name="Item Name",
            item_type=ItemType.FOLDER,
        )
        self.assertEqual(result, expected_result)
        self.onedrive_imp.network.GET.assert_called_with(
            "me/drive/items/item-id",
            query={"select": "id,name,folder,createdDateTime,lastModifiedDateTime"},
        )

    def test_list_child_items(self):
        mock_response = {
            "value": [
                {
                    "id": "item1-id",
                    "name": "Item 1",
                    "folder": {},
                    "createdDateTime": "2021-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2021-01-01T00:00:00Z",
                },
                {
                    "id": "item2-id",
                    "name": "Item 2",
                    "createdDateTime": "2021-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2021-01-01T00:00:00Z",
                },
            ],
            "@odata.nextLink": "https://graph.microsoft.com/nextPageLink",
        }
        self.onedrive_imp.network.GET.return_value.__aenter__.return_value.json_content = AsyncMock(
            return_value=mock_response
        )

        with patch("addon_imps.storage.onedrive.NextLinkCursor") as MockNextLinkCursor:
            mock_cursor_instance = MockNextLinkCursor.return_value
            mock_cursor_instance.this_cursor_str = (
                "https://graph.microsoft.com/nextPageLink"
            )

            result = asyncio.run(self.onedrive_imp.list_child_items("parent-item-id"))

            expected_items = [
                ItemResult(
                    item_id="item1-id",
                    item_name="Item 1",
                    item_type=ItemType.FOLDER,
                ),
                ItemResult(
                    item_id="item2-id",
                    item_name="Item 2",
                    item_type=ItemType.FILE,
                ),
            ]

            self.assertEqual(result.items, expected_items)

            self.assertEqual(
                result.this_sample_cursor, "https://graph.microsoft.com/nextPageLink"
            )

        self.onedrive_imp.network.GET.assert_called_with(
            "me/drive/items/parent-item-id/children",
            query={
                "select": "id,name,folder,createdDateTime,lastModifiedDateTime",
            },
        )

    def test_params_from_cursor(self):
        cursor = "https://graph.microsoft.com/v1.0/me/drive/items/parent-item-id/children?$skip=10&$top=5"
        expected_params = {"$skip": "10", "$top": "5"}
        result = self.onedrive_imp._params_from_cursor(cursor)
        self.assertEqual(result, expected_params)
        result = self.onedrive_imp._params_from_cursor("")
        self.assertEqual(result, {})
