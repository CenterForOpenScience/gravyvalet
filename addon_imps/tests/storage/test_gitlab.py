import unittest
from http import HTTPStatus
from unittest.mock import AsyncMock

from addon_imps.storage.gitlab import GitlabStorageImp
from addon_service.common.exceptions import ItemNotFound
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestGitlabStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://gitlab.com/api/v4"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=100)
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = GitlabStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value: dict | list, status=200, headers=None):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = status
        mock.headers = headers or {}

    def _assert_get(self, url: str, query: dict = None):
        extra_params = {"query": query} if query else {}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        mock_response = {"user_id": "12345"}
        self._patch_get(mock_response)

        result = await self.imp.get_external_account_id({})
        self.assertEqual(result, "12345")
        self._assert_get("user/preferences")

    async def test_list_root_items(self):
        mock_response = [
            {
                "id": "1",
                "name": "repo1",
                "path_with_namespace": "repo1",
            },
            {
                "id": "2",
                "name": "repo2",
                "path_with_namespace": "repo2",
            },
        ]
        self._patch_get(mock_response)

        result = await self.imp.list_root_items()
        expected_items = [
            ItemResult(item_id="repo1:", item_name="repo1", item_type=ItemType.FOLDER),
            ItemResult(item_id="repo2:", item_name="repo2", item_type=ItemType.FOLDER),
        ]
        expected_result = ItemSampleResult(items=expected_items)

        self.assertEqual(result.items, expected_result.items)
        self._assert_get(
            "projects",
            {
                "membership": "true",
                "simple": "true",
                "pagination": "true",
                "sort": "asc",
            },
        )

    async def test_get_item_info_repository(self):
        mock_response = {
            "id": "1",
            "name": "repo1",
            "path_with_namespace": "repo1",
        }
        self._patch_get(mock_response)
        result = await self.imp.get_item_info("1:")

        expected_result = ItemResult(
            item_id="repo1:", item_name="repo1", item_type=ItemType.FOLDER
        )
        self.assertEqual(result, expected_result)
        self._assert_get("projects/1")

    async def test_get_item_info_file(self):
        file_mock = {
            "file_name": "README.md",
            "path": "README.md",
        }

        self._patch_get(file_mock)
        result = await self.imp.get_item_info("1:README.md")
        expected_result = ItemResult(
            item_id="1:README.md", item_name="README.md", item_type=ItemType.FILE
        )
        self.assertEqual(result, expected_result)

    async def test_list_child_items_folder(self):
        folder_mock = [
            {
                "name": "src",
                "path": "src",
                "type": "tree",
            },
            {
                "name": "README.md",
                "path": "README.md",
                "type": "blob",
            },
        ]
        self._patch_get(folder_mock)

        result = await self.imp.list_child_items("1:")
        expected_items = [
            ItemResult(item_id="1:src", item_name="src", item_type=ItemType.FOLDER),
            ItemResult(
                item_id="1:README.md", item_name="README.md", item_type=ItemType.FILE
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items)

        self.assertEqual(result.items, expected_result.items)
        self._assert_get(
            "projects/1/repository/tree",
            {"pagination": "keyset", "path": "", "sort": "asc", "order_by": "name"},
        )

    async def test_get_item_info_file_not_found(self):
        self._patch_get({}, status=HTTPStatus.NOT_FOUND)

        with self.assertRaises(ItemNotFound):
            await self.imp.get_item_info("1:missing_file.md")

    async def test_list_child_items_not_found(self):
        self._patch_get({}, status=HTTPStatus.NOT_FOUND)

        with self.assertRaises(ItemNotFound):
            await self.imp.list_child_items(item_id="1:missing_folder")

    async def test_list_root_items_first_page(self):
        mock_response_page_1 = [
            {"id": "1", "name": "repo1", "path_with_namespace": "repo1"},
            {"id": "2", "name": "repo2", "path_with_namespace": "repo2"},
        ]
        self._patch_get(
            mock_response_page_1,
            headers={"Link": '<https://gitlab.com/api/v4/projects?page=2>; rel="next"'},
        )
        result_page_1 = await self.imp.list_root_items()
        expected_items_page_1 = [
            ItemResult(item_id="repo1:", item_name="repo1", item_type=ItemType.FOLDER),
            ItemResult(item_id="repo2:", item_name="repo2", item_type=ItemType.FOLDER),
        ]
        self.assertEqual(result_page_1.items, expected_items_page_1)
        self.assertEqual(result_page_1.next_sample_cursor, "page=2")

    async def test_list_root_items_second_page(self):
        mock_response_page_2 = [
            {"id": "3", "name": "repo3", "path_with_namespace": "repo3"},
        ]
        self._patch_get(mock_response_page_2, headers={})
        result_page_2 = await self.imp.list_root_items(page_cursor="page=2")
        expected_items_page_2 = [
            ItemResult(item_id="repo3:", item_name="repo3", item_type=ItemType.FOLDER),
        ]
        self.assertEqual(result_page_2.items, expected_items_page_2)
        self.assertIsNone(result_page_2.next_sample_cursor)

    async def test_list_child_items_first_page(self):
        folder_mock_page_1 = [
            {"name": "src", "path": "src", "type": "tree"},
            {"name": "README.md", "path": "README.md", "type": "blob"},
        ]
        self._patch_get(
            folder_mock_page_1,
            headers={
                "Link": '<https://gitlab.com/api/v4/projects/1/repository/tree?page=2>; rel="next"'
            },
        )
        result_page_1 = await self.imp.list_child_items("1:")
        expected_items_page_1 = [
            ItemResult(item_id="1:src", item_name="src", item_type=ItemType.FOLDER),
            ItemResult(
                item_id="1:README.md", item_name="README.md", item_type=ItemType.FILE
            ),
        ]
        self.assertEqual(result_page_1.items, expected_items_page_1)
        self.assertEqual(result_page_1.next_sample_cursor, "page=2")

    async def test_list_child_items_second_page(self):
        folder_mock_page_2 = [
            {"name": "LICENSE", "path": "LICENSE", "type": "blob"},
        ]
        self._patch_get(folder_mock_page_2, headers={})
        result_page_2 = await self.imp.list_child_items("1:", page_cursor="page=2")
        expected_items_page_2 = [
            ItemResult(
                item_id="1:LICENSE", item_name="LICENSE", item_type=ItemType.FILE
            ),
        ]
        self.assertEqual(result_page_2.items, expected_items_page_2)
        self.assertIsNone(result_page_2.next_sample_cursor)
