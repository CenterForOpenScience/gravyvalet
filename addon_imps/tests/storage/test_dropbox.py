import unittest
from unittest.mock import (
    AsyncMock,
    call,
)

from addon_imps.storage.dropbox import DropboxStorageImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestDropboxStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://api.dropboxapi.com"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=123)
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = DropboxStorageImp(config=self.config, network=self.network)

    def _patch_post(self, return_value: dict):
        mock = self.network.POST.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_post(self, url: str, json: dict):
        expected_calls = [
            call(url, json=json),
            call().__aenter__(),
            call().__aenter__().json_content(),
            call().__aexit__(None, None, None),
        ]
        self.network.POST.assert_has_calls(expected_calls)

    async def test_get_external_account_id(self):
        result = await self.imp.get_external_account_id({})
        self.assertEqual(result, "")
        self.network.POST.assert_not_called()

    async def test_list_root_items(self):
        mock_response = {
            "entries": [{"id": "123", "name": "root folder", ".tag": "folder"}],
            "cursor": "test_cursor",
        }
        self._patch_post(mock_response)

        result = await self.imp.list_root_items()

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="123", item_name="root folder", item_type=ItemType.FOLDER
                )
            ],
            total_count=1,
            next_sample_cursor="test_cursor",
        )

        self.assertEqual(result, expected_result)
        self._assert_post("files/list_folder", json={"path": "", "recursive": False})

    async def test_get_item_info(self):
        cases = [("", "root folder"), ("file_id", "file")]
        for item_id, item_name in cases:
            with self.subTest(item_id=item_id):
                mock_response = {
                    "id": item_id or "",
                    "name": item_name,
                    ".tag": "folder" if not item_id else "file",
                }
                self._patch_post(mock_response)

                result = await self.imp.get_item_info(item_id)

                expected_result = ItemResult(
                    item_id=item_id or "",
                    item_name=item_name,
                    item_type=ItemType.FOLDER if not item_id else ItemType.FILE,
                )
                self.assertEqual(result, expected_result)

                expected_json = {"path": item_id or ""}
                if expected_json["path"] != "":
                    self._assert_post("files/get_metadata", json=expected_json)

    async def test_list_child_items(self):
        mock_response = {
            "entries": [
                {"id": "123", "name": "child folder", ".tag": "folder"},
                {"id": "456", "name": "child file", ".tag": "file"},
            ],
            "cursor": "test_cursor",
        }
        self._patch_post(mock_response)

        result = await self.imp.list_child_items(item_id="test_id")

        expected_result = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="123", item_name="child folder", item_type=ItemType.FOLDER
                ),
                ItemResult(
                    item_id="456", item_name="child file", item_type=ItemType.FILE
                ),
            ],
            total_count=2,
            next_sample_cursor="test_cursor",
        )

        self.assertEqual(result, expected_result)
        self._assert_post(
            "files/list_folder", json={"path": "test_id", "recursive": False}
        )

        mock_response_continue = {
            "entries": [{"id": "789", "name": "another child file", ".tag": "file"}],
            "cursor": "next_cursor",
        }
        self._patch_post(mock_response_continue)

        result = await self.imp.list_child_items(
            item_id="test_id", page_cursor="test_cursor"
        )

        expected_result_continue = ItemSampleResult(
            items=[
                ItemResult(
                    item_id="789",
                    item_name="another child file",
                    item_type=ItemType.FILE,
                )
            ],
            total_count=1,
            next_sample_cursor="next_cursor",
        )

        self.assertEqual(result, expected_result_continue)

        self.network.POST.assert_has_calls(
            [
                call("files/list_folder", json={"path": "test_id", "recursive": False}),
                call().__aenter__(),
                call().__aenter__().json_content(),
                call().__aexit__(None, None, None),
                call("files/list_folder/continue", json={"cursor": "test_cursor"}),
                call().__aenter__(),
                call().__aenter__().json_content(),
                call().__aexit__(None, None, None),
            ]
        )
