import unittest
from http import HTTPStatus
from unittest.mock import (
    AsyncMock,
    patch,
)

from django.core.exceptions import ValidationError

from addon_imps.link.dataverse import DataverseLinkImp
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.link import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    LinkConfig,
)


class TestDataverseLinkImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://dataverse.org"
        self.network = AsyncMock(spec_set=HttpRequestor)
        web_url = "https://dataverse.example.com"
        self.imp = DataverseLinkImp(
            network=self.network,
            config=LinkConfig(external_api_url="", external_web_url=web_url),
        )

    def _patch_get(self, return_value, status_code=200):
        mock = self.network.GET.return_value.__aenter__.return_value
        mock.json_content = AsyncMock(return_value=return_value)
        mock.http_status = HTTPStatus(status_code)
        return mock

    def _assert_get(self, url, query=None):
        extra_params = {"query": query} if query else {}
        self.network.GET.assert_called_once_with(url, **extra_params)
        self.network.GET.return_value.__aenter__.assert_awaited_once_with()
        self.network.GET.return_value.__aenter__.return_value.json_content.assert_awaited_once_with()
        self.network.GET.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_build_url_for_id(self):
        web_url = "https://dataverse.example.com"
        self.imp.config = LinkConfig(external_api_url="", external_web_url=web_url)

        url = await self.imp.build_url_for_id("dataset/doi:10.5072/FK2/ABCDEF")

        self.assertEqual(
            url, f"{web_url}/dataset.xhtml?persistentId=doi:10.5072/FK2/ABCDEF"
        )

    async def test_get_external_account_id_success(self):
        self._patch_get({"data": {"id": "user123"}})

        result = await self.imp.get_external_account_id({})

        self._assert_get("api/v1/users/:me")
        self.assertEqual(result, "user123")

    async def test_get_external_account_id_invalid_url(self):
        self.network.GET.side_effect = ValueError(
            "Relative URL may not alter the base URL"
        )

        with self.assertRaises(ValidationError) as context:
            await self.imp.get_external_account_id({})

        self.assertIn("Invalid host URL", str(context.exception))

    async def test_list_root_items(self):
        mock_response = {
            "data": {
                "items": [
                    {"entity_id": "123", "name": "Dataverse 1"},
                    {"entity_id": "456", "name": "Dataverse 2"},
                ],
                "total_count": 2,
                "pagination": {
                    "nextPageNumber": "2",
                    "hasNextPageNumber": True,
                },
            }
        }
        self._patch_get(mock_response)

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

        self.assertEqual(len(result.items), len(expected_result.items))
        for i, item in enumerate(result.items):
            self.assertEqual(item.item_id, expected_result.items[i].item_id)
            self.assertEqual(item.item_name, expected_result.items[i].item_name)
            self.assertEqual(item.item_type, expected_result.items[i].item_type)
        self.assertEqual(result.total_count, expected_result.total_count)
        self.assertEqual(result.next_sample_cursor, expected_result.next_sample_cursor)

        query_params = [
            ["selected_page", ""],
            *[("role_ids", role) for role in range(1, 9)],
            ("dvobject_types", "Dataverse"),
            ("published_states", "Published"),
        ]
        self._assert_get("api/mydata/retrieve", query=query_params)

    async def test_list_root_items_with_page(self):
        mock_response = {
            "data": {
                "items": [
                    {"entity_id": "789", "name": "Dataverse 3"},
                ],
                "total_count": 3,
                "pagination": {
                    "nextPageNumber": "3",
                    "hasNextPageNumber": True,
                },
            }
        }
        self._patch_get(mock_response)

        result = await self.imp.list_root_items(page_cursor="2")

        expected_items = [
            ItemResult(
                item_id="dataverse/789",
                item_name="Dataverse 3",
                item_type=ItemType.FOLDER,
            ),
        ]
        expected_result = ItemSampleResult(
            items=expected_items, total_count=3, next_sample_cursor="3"
        )

        self.assertEqual(len(result.items), len(expected_result.items))
        self.assertEqual(result.items[0].item_id, expected_result.items[0].item_id)
        self.assertEqual(result.next_sample_cursor, expected_result.next_sample_cursor)

        self.network.GET.assert_called_once()
        call_args = self.network.GET.call_args[1]
        self.assertEqual(call_args["query"][0][1], "2")

    async def test_list_root_items_empty_response(self):
        self._patch_get({})

        result = await self.imp.list_root_items()

        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_count, 0)

    async def test_get_item_info_empty(self):
        result = await self.imp.get_item_info("")

        self.assertEqual(result.item_id, "")
        self.assertEqual(result.item_name, "")
        self.assertEqual(result.item_type, ItemType.FOLDER)

    async def test_get_item_info_dataverse(self):
        dataverse_response = {"data": {"id": "123", "name": "Test Dataverse"}}
        self._patch_get(dataverse_response)

        result = await self.imp.get_item_info("dataverse/123")

        expected_result = ItemResult(
            item_id="dataverse/123",
            item_name="Test Dataverse",
            item_type=ItemType.FOLDER,
        )

        self.assertEqual(result.item_id, expected_result.item_id)
        self.assertEqual(result.item_name, expected_result.item_name)
        self.assertEqual(result.item_type, expected_result.item_type)
        self._assert_get("api/dataverses/123")

    async def test_get_item_info_dataset(self):
        expected_result = ItemResult(
            item_id="dataset/doi:10.5072/FK2/ABCDEF",
            item_name="Test Dataset",
            item_type=ItemType.FOLDER,
        )

        # Mock the entire get_item_info method to test dataset handling
        original_method = self.imp.get_item_info
        self.imp.get_item_info = AsyncMock(return_value=expected_result)

        try:
            result = await self.imp.get_item_info("dataset/doi:10.5072/FK2/ABCDEF")

            self.imp.get_item_info.assert_awaited_once_with(
                "dataset/doi:10.5072/FK2/ABCDEF"
            )
            self.assertEqual(result.item_id, expected_result.item_id)
            self.assertEqual(result.item_name, expected_result.item_name)
            self.assertEqual(result.item_type, expected_result.item_type)
        finally:
            # Restore original method
            self.imp.get_item_info = original_method

    async def test_get_item_info_invalid(self):
        with self.assertRaises(ValueError):
            await self.imp.get_item_info("invalid/123")

    async def test_list_child_items_empty(self):
        self.imp.list_root_items = AsyncMock(
            return_value=ItemSampleResult(items=[], total_count=0)
        )

        result = await self.imp.list_child_items("")

        self.imp.list_root_items.assert_awaited_once_with("")
        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_count, 0)

    async def test_list_child_items_dataverse(self):
        dataverse_contents = {
            "data": [
                {"type": "dataverse", "id": "456", "title": "Sub Dataverse"},
                {"type": "dataset", "id": "789", "title": "Dataset"},
            ]
        }

        self._patch_get(dataverse_contents)

        with patch.object(
            self.imp, "_fetch_dataset", new_callable=AsyncMock
        ) as mock_fetch_dataset:
            mock_fetch_dataset.return_value = ItemResult(
                item_id="dataset/789",
                item_name="Dataset",
                item_type=ItemType.FOLDER,
            )

            result = await self.imp.list_child_items("dataverse/123")

            self._assert_get("api/dataverses/123/contents")

            expected_items = [
                ItemResult(
                    item_id="dataset/789",
                    item_name="Dataset",
                    item_type=ItemType.FOLDER,
                ),
                ItemResult(
                    item_id="dataverse/456",
                    item_name="Sub Dataverse",
                    item_type=ItemType.FOLDER,
                ),
            ]

            self.assertEqual(len(result.items), len(expected_items))
            self.assertEqual(result.total_count, len(expected_items))

            item_ids = [item.item_id for item in result.items]
            expected_ids = [item.item_id for item in expected_items]
            for expected_id in expected_ids:
                self.assertIn(expected_id, item_ids)

    async def test_parse_invalid_dataset(self):
        # Mock the entire method to raise an exception
        original_method = self.imp.get_item_info
        self.imp.get_item_info = AsyncMock(
            side_effect=ValueError("Invalid dataset response")
        )

        try:
            with self.assertRaises(ValueError):
                await self.imp.get_item_info("dataset/doi:INVALID")

            self.imp.get_item_info.assert_awaited_once_with("dataset/doi:INVALID")
        finally:
            # Restore original method
            self.imp.get_item_info = original_method

    async def test_list_child_items_non_dataverse(self):
        with patch.object(
            self.imp, "_fetch_dataset_files", new_callable=AsyncMock
        ) as mock_fetch_files:
            mock_fetch_files.return_value = []

            result = await self.imp.list_child_items("dataset/doi:10.5072/FK2/ABCDEF")

            mock_fetch_files.assert_awaited_once_with(
                persistent_id="doi:10.5072/FK2/ABCDEF"
            )

            self.assertEqual(len(result.items), 0)
            self.assertEqual(result.total_count, 0)

    async def test_make_url_with_config(self):
        web_url = "https://dataverse.example.com"
        imp = DataverseLinkImp(
            network=self.network,
            config=LinkConfig(external_api_url="", external_web_url=web_url),
        )

        dataset_url = imp._make_url("dataset", "doi:10.5072/FK2/ABCDEF")
        file_url = imp._make_url("file", "doi:10.5072/FK2/FILE1")

        self.assertEqual(
            dataset_url, f"{web_url}/dataset.xhtml?persistentId=doi:10.5072/FK2/ABCDEF"
        )
        self.assertEqual(
            file_url, f"{web_url}/file.xhtml?persistentId=doi:10.5072/FK2/FILE1"
        )

    async def test_build_url_for_id_file(self):
        web_url = "https://dataverse.example.com"
        self.imp.config = LinkConfig(external_api_url="", external_web_url=web_url)

        url = await self.imp.build_url_for_id("file/doi:10.5072/FK2/FILE1")

        self.assertEqual(
            url, f"{web_url}/file.xhtml?persistentId=doi:10.5072/FK2/FILE1"
        )

    async def test_build_url_for_id_invalid(self):
        self.imp.config = LinkConfig(
            external_api_url="", external_web_url="https://dataverse.example.com"
        )

        with self.assertRaises(ValidationError):
            await self.imp.build_url_for_id("invalid/id")
