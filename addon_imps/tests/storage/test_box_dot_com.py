import unittest
from unittest.mock import (
    AsyncMock,
    call,
)

from addon_imps.storage.box_dot_com import BoxDotComStorageImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.cursor import OffsetCursor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestBoxDotComStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://api.box.com"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=100)
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = BoxDotComStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value: dict):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_get(self, url: str, query: dict = None):
        expected_calls = []
        if query is None:
            expected_calls.append(call(url))
        else:
            expected_calls.append(call(url, query=query))
        expected_calls.extend(
            [
                call().__aenter__(),
                call().__aenter__().json_content(),
                call().__aexit__(None, None, None),
            ]
        )
        self.network.GET.assert_has_calls(expected_calls)

    async def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self._patch_get(mock_response)

        result = await self.imp.get_external_account_id({})

        self.assertEqual(result, "12345")
        self._assert_get("users/me")

    async def test_list_root_items(self):
        root_id = "folder:0"
        mock_item_response = {
            "id": "0",
            "name": "root folder",
            "type": "folder",
            "path_collection": {"entries": []},
        }
        self._patch_get(mock_item_response)

        result = await self.imp.list_root_items()

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id=root_id,
                    item_name="root folder",
                    item_type=ItemType.FOLDER,
                    item_path=[],
                )
            ],
            total_count=1,
        )

        self.assertEqual(result, expected_result)
        self._assert_get("folders/0", query={"fields": "id,type,name,path"})

    async def test_get_item_info(self):
        cases = [
            ("folder:12345", {"id": "12345", "name": "test folder", "type": "folder"}),
            ("file:67890", {"id": "67890", "name": "test file", "type": "file"}),
        ]

        for item_id, mock_response in cases:
            with self.subTest(item_id=item_id):
                self._patch_get(mock_response)

                result = await self.imp.get_item_info(item_id)

                expected_result = ItemResult(
                    item_id=item_id,
                    item_name=mock_response["name"],
                    item_type=ItemType.FOLDER if "folder" in item_id else ItemType.FILE,
                )

                self.assertEqual(result, expected_result)
                self._assert_get(
                    (
                        f"folders/{mock_response['id']}"
                        if "folder" in item_id
                        else f"files/{mock_response['id']}"
                    ),
                    query={"fields": "id,type,name,path"},
                )

    async def test_list_child_items(self):
        item_id = "folder:12345"
        mock_response = {
            "entries": [
                {"id": "234", "name": "child folder", "type": "folder"},
                {"id": "345", "name": "child file", "type": "file"},
            ],
            "offset": 0,
            "limit": 100,
            "total_count": 2,
        }
        self._patch_get(mock_response)

        result = await self.imp.list_child_items(item_id)

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="folder:234",
                    item_name="child folder",
                    item_type=ItemType.FOLDER,
                ),
                ItemResult(
                    item_id="file:345", item_name="child file", item_type=ItemType.FILE
                ),
            ]
        ).with_cursor(OffsetCursor(offset=0, limit=100, total_count=2))

        self.assertEqual(result, expected_result)
        self._assert_get("folders/12345/items", query={"fields": "id,type,name"})

    async def test_list_child_items_with_cursor(self):
        item_id = "folder:12345"
        page_cursor = "0:100"
        mock_response = {
            "entries": [{"id": "456", "name": "another child file", "type": "file"}],
            "offset": 100,
            "limit": 100,
            "total_count": 3,
        }
        self._patch_get(mock_response)

        result = await self.imp.list_child_items(item_id, page_cursor)

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="file:456",
                    item_name="another child file",
                    item_type=ItemType.FILE,
                )
            ]
        ).with_cursor(OffsetCursor(offset=100, limit=100, total_count=3))

        self.assertEqual(result, expected_result)
        self._assert_get("folders/12345/items", query={"fields": "id,type,name"})
        result = await self.imp.list_child_items(item_id, page_cursor)

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="file:456",
                    item_name="another child file",
                    item_type=ItemType.FILE,
                )
            ]
        ).with_cursor(OffsetCursor(offset=100, limit=100, total_count=3))

        self.assertEqual(result, expected_result)
        self._assert_get("folders/12345/items", query={"fields": "id,type,name"})
