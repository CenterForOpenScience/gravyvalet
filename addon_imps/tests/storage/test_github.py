import unittest
from unittest.mock import AsyncMock

from addon_imps.storage.github import GitHubStorageImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestGitHubStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://api.github.com"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=100)
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = GitHubStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value: dict):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_get(self, url: str, query: dict = None):
        extra_params = {"query": query} if query else {}
        if url == "repos/testuser/repo1/contents/":
            extra_params = {"query": {}}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        mock_response = {"id": "12345"}
        self._patch_get(mock_response)
        result = await self.imp.get_external_account_id({})
        self.assertEqual(result, "12345")
        self._assert_get("user")

    async def test_list_root_items(self):
        mock_response = [
            {
                "id": 1,
                "full_name": "testuser/repo1",
                "name": "repo1",
                "private": False,
                "owner": {
                    "login": "testuser",
                },
            },
            {
                "id": 2,
                "full_name": "testuser/repo2",
                "name": "repo2",
                "private": False,
                "owner": {
                    "login": "testuser",
                },
            },
        ]
        self._patch_get(mock_response)

        result = await self.imp.list_root_items()
        expected_items = [
            ItemResult(
                item_id="testuser/repo1:", item_name="repo1", item_type=ItemType.FOLDER
            ),
            ItemResult(
                item_id="testuser/repo2:", item_name="repo2", item_type=ItemType.FOLDER
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items, total_count=2)
        self.assertEqual(result.items, expected_result.items)
        self.assertEqual(result.total_count, expected_result.total_count)
        self._assert_get("user/repos")

    async def test_get_item_info_root(self):
        result = await self.imp.get_item_info(".")
        expected_result = ItemResult(
            item_id="", item_name="GitHub", item_type=ItemType.FOLDER
        )
        self.assertEqual(result, expected_result)

    async def test_get_item_info_repo(self):
        mock_response = {
            "id": 1,
            "full_name": "testuser/repo1",
            "name": "repo1",
            "private": False,
            "owner": {
                "login": "testuser",
            },
        }
        self._patch_get(mock_response)
        result = await self.imp.get_item_info("testuser/repo1:")
        expected_result = ItemResult(
            item_id="testuser/repo1:", item_name="repo1", item_type=ItemType.FOLDER
        )
        self.assertEqual(result, expected_result)
        self._assert_get("repos/testuser/repo1")

    async def test_get_item_info_file(self):
        mock_response = {
            "name": "README.md",
            "path": "README.md",
            "type": "file",
        }
        self._patch_get(mock_response)
        result = await self.imp.get_item_info("testuser/repo1:README.md")

        expected_result = ItemResult(
            item_id="README.md", item_name="README.md", item_type=ItemType.FILE
        )
        self.assertEqual(result, expected_result)
        self._assert_get("repos/testuser/repo1/contents/README.md")

    async def test_list_child_items(self):
        mock_response = [
            {
                "name": "src",
                "path": "src",
                "type": "dir",
            },
            {
                "name": "README.md",
                "path": "README.md",
                "type": "file",
            },
        ]
        self._patch_get(mock_response)

        result = await self.imp.list_child_items("testuser/repo1:")
        expected_items = [
            ItemResult(
                item_id="testuser/repo1:src", item_name="src", item_type=ItemType.FOLDER
            ),
            ItemResult(
                item_id="README.md", item_name="README.md", item_type=ItemType.FILE
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items, total_count=2)
        self.assertEqual(result.items, expected_result.items)
        self.assertEqual(result.total_count, expected_result.total_count)
        self._assert_get("repos/testuser/repo1/contents/")
