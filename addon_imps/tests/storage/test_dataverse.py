import unittest
from unittest.mock import AsyncMock

from addon_imps.storage.dataverse import DataverseStorageImp
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    StorageConfig,
)


class TestDataverseStorageImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://dataverse.org/api"
        self.config = StorageConfig(external_api_url=self.base_url, max_upload_mb=100)
        self.network = AsyncMock()
        self.imp = DataverseStorageImp(config=self.config, network=self.network)

    def _patch_get(self, return_value):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_get(self, url, query=None):
        extra_params = {"query": query} if query else {}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once_with()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once_with()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        result = await self.imp.get_external_account_id({})
        self.assertEqual(result, "")

    async def test_list_root_items(self):
        mock_response = {
            "data": {
                "items": [
                    {"entity_id": "123", "name": "Dataverse 1"},
                    {"entity_id": "456", "name": "Dataverse 2"},
                ],
                "total_count": 2,
                "pagination": {"nextPageNumber": "2"},
            }
        }
        self._patch_get(mock_response)
        self.imp.list_root_items = AsyncMock(
            spec_set=self.imp.list_root_items,
            return_value=ItemSampleResult(
                items=[
                    ItemResult(
                        item_id="dataverse/123",
                        item_name="Dataverse 1",
                        item_type=ItemType.FOLDER,
                    ),
                    ItemResult(
                        item_id="dataverse/456",
                        item_name="Dataverse 2",
                        item_type=ItemType.FOLDER,
                    ),
                ],
                total_count=2,
                next_sample_cursor="2",
            ),
        )
        result = await self.imp.list_root_items()
        expected_items = [
            ItemResult(
                item_id="dataverse/123",
                item_name="Dataverse 1",
                item_type=ItemType.FOLDER,
            ),
            ItemResult(
                item_id="dataverse/456",
                item_name="Dataverse 2",
                item_type=ItemType.FOLDER,
            ),
        ]
        expected_result = ItemSampleResult(
            items=expected_items, total_count=2, next_sample_cursor="2"
        )
        self.assertEqual(result.items, expected_result.items)
        self.assertEqual(result.total_count, expected_result.total_count)
        self.imp.list_root_items.assert_awaited_once_with()

    async def test_get_item_info_dataverse(self):
        mock_response = {"data": {"id": "123", "name": "Sample Dataverse"}}
        self._patch_get(mock_response)
        self.imp._fetch_dataverse = AsyncMock(
            spec_set=self.imp._fetch_dataverse,
            return_value=ItemResult(
                item_id="dataverse/123",
                item_name="Sample Dataverse",
                item_type=ItemType.FOLDER,
            ),
        )
        result = await self.imp.get_item_info("dataverse/123")
        expected_result = ItemResult(
            item_id="dataverse/123",
            item_name="Sample Dataverse",
            item_type=ItemType.FOLDER,
        )
        self.assertEqual(result, expected_result)
        self.imp._fetch_dataverse.assert_awaited_once_with("123")

    async def test_get_item_info_dataset(self):
        mock_response = {
            "data": {
                "id": "456",
                "latestVersion": {
                    "metadataBlocks": {
                        "citation": {
                            "fields": [{"typeName": "title", "value": "Sample Dataset"}]
                        }
                    }
                },
            }
        }
        self._patch_get(mock_response)
        self.imp._fetch_dataset = AsyncMock(
            spec_set=self.imp._fetch_dataset,
            return_value=ItemResult(
                item_id="dataset/456",
                item_name="Sample Dataset",
                item_type=ItemType.FOLDER,
            ),
        )
        result = await self.imp.get_item_info("dataset/456")
        expected_result = ItemResult(
            item_id="dataset/456", item_name="Sample Dataset", item_type=ItemType.FOLDER
        )
        self.assertEqual(result, expected_result)

    async def test_get_item_info_file(self):
        mock_response = {"data": {"dataFile": {"id": "789"}, "label": "Sample File"}}
        self._patch_get(mock_response)
        self.imp._fetch_file = AsyncMock(
            spec_set=self.imp._fetch_file,
            return_value=ItemResult(
                item_id="file/789", item_name="Sample File", item_type=ItemType.FILE
            ),
        )
        result = await self.imp.get_item_info("file/789")
        expected_result = ItemResult(
            item_id="file/789", item_name="Sample File", item_type=ItemType.FILE
        )
        self.assertEqual(result, expected_result)
        self.imp._fetch_file.assert_awaited_once_with("789")

    async def test_list_child_items_dataverse(self):
        mock_response = {
            "data": [
                {"type": "dataset", "id": "456", "title": "Dataset 1"},
                {"type": "dataverse", "id": "123", "title": "Sub-Dataverse"},
            ]
        }
        self._patch_get(mock_response)
        self.imp._fetch_dataverse_items = AsyncMock(
            spec_set=self.imp._fetch_dataverse_items,
            return_value=[
                ItemResult(
                    item_id="dataset/456",
                    item_name="Dataset 1",
                    item_type=ItemType.FOLDER,
                ),
                ItemResult(
                    item_id="dataverse/123",
                    item_name="Sub-Dataverse",
                    item_type=ItemType.FOLDER,
                ),
            ],
        )
        result = await self.imp.list_child_items("dataverse/123")
        expected_items = [
            ItemResult(
                item_id="dataset/456", item_name="Dataset 1", item_type=ItemType.FOLDER
            ),
            ItemResult(
                item_id="dataverse/123",
                item_name="Sub-Dataverse",
                item_type=ItemType.FOLDER,
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items, total_count=2)
        self.assertEqual(result.items, expected_result.items)
        self.imp._fetch_dataverse_items.assert_awaited_once_with("123")

    async def test_list_child_items_dataset_files(self):
        mock_response = {
            "data": {
                "latestVersion": {
                    "files": [
                        {"dataFile": {"id": "789"}, "label": "File 1"},
                        {"dataFile": {"id": "1011"}, "label": "File 2"},
                    ]
                }
            }
        }
        self._patch_get(mock_response)
        self.imp._fetch_dataset_files = AsyncMock(
            spec_set=self.imp._fetch_dataset_files,
            return_value=[
                ItemResult(
                    item_id="file/789", item_name="File 1", item_type=ItemType.FILE
                ),
                ItemResult(
                    item_id="file/1011", item_name="File 2", item_type=ItemType.FILE
                ),
            ],
        )
        result = await self.imp.list_child_items("dataset/456", item_type=ItemType.FILE)
        expected_items = [
            ItemResult(item_id="file/789", item_name="File 1", item_type=ItemType.FILE),
            ItemResult(
                item_id="file/1011", item_name="File 2", item_type=ItemType.FILE
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items, total_count=2)
        self.assertEqual(result.items, expected_result.items)
        self.assertEqual(result.total_count, expected_result.total_count)
        self.imp._fetch_dataset_files.assert_awaited_once_with("456")
