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
)


class TestDataverseLinkImp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base_url = "https://dataverse.org"
        self.network = AsyncMock(spec_set=HttpRequestor)
        self.imp = DataverseLinkImp(network=self.network)

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
        dataset_result = ItemResult(
            item_id="dataset/doi:10.5072/FK2/ABCDEF",
            item_name="Test Dataset",
            item_type=ItemType.FOLDER,
        )

        with patch.object(
            self.imp, "_fetch_dataset", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = dataset_result

            url = await self.imp.build_url_for_id("dataset/doi:10.5072/FK2/ABCDEF")

            mock_fetch.assert_awaited_once_with("doi:10.5072/FK2/ABCDEF")

            self.assertEqual(url, "dataset/doi:10.5072/FK2/ABCDEF")

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
            *[
                ("published_states", state)
                for state in [
                    "Unpublished",
                    "Published",
                    "Draft",
                    "Deaccessioned",
                    "In+Review",
                ]
            ],
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
        dataset_response = {
            "data": {
                "latestVersion": {
                    "datasetPersistentId": "doi:10.5072/FK2/ABCDEF",
                    "metadataBlocks": {
                        "citation": {
                            "fields": [{"typeName": "title", "value": "Test Dataset"}]
                        }
                    },
                }
            }
        }
        self._patch_get(dataset_response)

        result = await self.imp.get_item_info("dataset/doi:10.5072/FK2/ABCDEF")

        expected_result = ItemResult(
            item_id="dataset/doi:10.5072/FK2/ABCDEF",
            item_name="Test Dataset",
            item_type=ItemType.FOLDER,
        )

        self.assertEqual(result.item_id, expected_result.item_id)
        self.assertEqual(result.item_name, expected_result.item_name)
        self.assertEqual(result.item_type, expected_result.item_type)
        self._assert_get(
            "api/datasets/:persistentId",
            query={"persistentId": "doi:10.5072/FK2/ABCDEF"},
        )

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
        invalid_dataset = {"data": {}}
        self._patch_get(invalid_dataset)

        with self.assertRaises(ValueError):
            await self.imp.get_item_info("dataset/invalid")

    async def test_list_child_items_non_dataverse(self):
        result = await self.imp.list_child_items("dataset/123")

        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_count, 0)
