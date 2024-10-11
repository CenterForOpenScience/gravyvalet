import unittest
from collections import namedtuple
from unittest.mock import (
    AsyncMock,
    sentinel,
)

from addon_imps.storage.google_drive import (
    File,
    GoogleDriveStorageImp,
)
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestGoogleDriveStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://google-drive-api.com"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=123)
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = GoogleDriveStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value: dict | list | str):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_get(self, url: str, query: dict = None):
        extra_params = {"query": query} if query else {}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once_with()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once_with()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self._patch_get(mock_response)

        result = await self.imp.get_external_account_id({})

        self.assertEqual(result, "")
        self.network.GET.assert_not_called()

    async def test_list_root_items(self):
        mock_response = sentinel.result

        self.imp.get_item_info = AsyncMock(
            spec_set=self.imp.get_item_info, return_value=mock_response
        )

        result = await self.imp.list_root_items()

        expected_result = ItemSampleResult(
            items=[mock_response],
            total_count=1,
        )

        self.assertEqual(expected_result, result)
        self.imp.get_item_info.assert_awaited_once_with("root")

    async def test_list_child_items(self):
        args = namedtuple(
            "Args", ["item_id", "page_cursor", "item_type", "expected_query"]
        )
        cases = [
            args("root", None, None, {"q": "'root' in parents"}),
            args("root", "root", None, {"q": "'root' in parents", "pageToken": "root"}),
            args(
                "root",
                None,
                ItemType.FOLDER,
                {
                    "q": "'root' in parents and mimeType='application/vnd.google-apps.folder'"
                },
            ),
            args(
                "root",
                None,
                ItemType.FILE,
                {
                    "q": "'root' in parents and mimeType!='application/vnd.google-apps.folder'"
                },
            ),
            args(
                "root",
                "token",
                ItemType.FILE,
                {
                    "q": "'root' in parents and mimeType!='application/vnd.google-apps.folder'",
                    "pageToken": "token",
                },
            ),
            args(
                "root",
                "token",
                ItemType.FOLDER,
                {
                    "q": "'root' in parents and mimeType='application/vnd.google-apps.folder'",
                    "pageToken": "token",
                },
            ),
        ]
        for case in cases:
            self.network.reset_mock()
            with self.subTest(case=f"case: {case=}"):
                await self._test_list_collection_items_ordinary(*case)

    async def _test_list_collection_items_ordinary(
        self,
        item_id: str,
        page_cursor: str | None,
        item_type,
        expected_query: dict,
    ) -> None:
        self._patch_get(
            {
                "files": [
                    {
                        "kind": "drive#file",
                        "driveId": "123",
                        "extra_attribute": "dasdasd",
                        "mimeType": "application/vnd.google-apps.folder",
                        "name": "foobar",
                        "id": "1023",
                    }
                ],
                "nextPageToken": "<PASSWORD>",
                "kind": "drive#fileList",
                "incompleteSearch": False,
            }
        )
        result = await self.imp.list_child_items(
            item_id,
            page_cursor=page_cursor,
            item_type=item_type,
        )
        self._assert_get(
            "drive/v3/files",
            query=expected_query,
        )
        assert result == ItemSampleResult(
            total_count=1,
            next_sample_cursor="<PASSWORD>",
            items=[
                ItemResult(
                    item_id="1023",
                    item_name="foobar",
                    item_type=ItemType.FOLDER,
                )
            ],
        )

    async def test_get_item_info(self):
        cases = [("", "root"), ("foo", "foo")]
        for item_id in cases:
            self.network.reset_mock()
            with self.subTest(case=f"case: {item_id=}"):
                await self._test_item_info(*item_id)

    async def _test_item_info(self, item_id: str, url_segment: str):
        self._patch_get(
            {
                "kind": "drive#file",
                "driveId": "123",
                "extra_attribute": "dasdasd",
                "mimeType": "application/vnd.google-apps.folder",
                "name": "foobar",
                "id": "1023",
            }
        )
        result = await self.imp.get_item_info(item_id)
        self._assert_get(f"drive/v3/files/{url_segment}")
        assert result == ItemResult(
            item_id="1023", item_name="foobar", item_type=ItemType.FOLDER
        )

    def test_parse_file(self):
        assert File(
            mimeType="application/vnd.google-apps.folder", name="folder", id="folder_id"
        ).item_result == ItemResult(
            item_id="folder_id", item_name="folder", item_type=ItemType.FOLDER
        )
        assert File(
            mimeType="application/vnd.google-apps.file", name="folder", id="folder_id"
        ).item_result == ItemResult(
            item_id="folder_id", item_name="folder", item_type=ItemType.FILE
        )
        assert (
            File.from_json(
                {
                    "mimeType": "application/vnd.google-apps.file",
                    "name": "file",
                    "id": "file_id",
                    "lkaasdasdasdasd": "dasduhasgjdjgas",
                },
            )
            == File.from_json(
                {
                    "mimeType": "application/vnd.google-apps.file",
                    "name": "file",
                    "id": "file_id",
                }
            )
            == File(
                mimeType="application/vnd.google-apps.file", name="file", id="file_id"
            )
        )
