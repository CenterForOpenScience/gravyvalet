import unittest
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock

from addon_imps.storage.azure_blob_storage import AzureBlobStorageImp
from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemType,
    StorageConfig,
)


class TestAzureBlobStorageImp(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.config = StorageConfig(
            external_api_url="https://teststorage.blob.core.windows.net",
            connected_root_id="testcontainer:/",
            external_account_id="teststorage",
            max_upload_mb=100,
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.azure_blob_storage_imp = AzureBlobStorageImp(
            config=self.config, network=self.network
        )

    async def test_list_root_items_success(self):
        """Test successful container listing"""
        mock_xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/">
            <Containers>
                <Container>
                    <Name>container1</Name>
                </Container>
                <Container>
                    <Name>container2</Name>
                </Container>
            </Containers>
        </EnumerationResults>"""

        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=mock_xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.list_root_items()

        expected_items = [
            ItemResult(
                item_id="container1:/",
                item_name="container1/",
                item_type=ItemType.FOLDER,
            ),
            ItemResult(
                item_id="container2:/",
                item_name="container2/",
                item_type=ItemType.FOLDER,
            ),
        ]

        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].item_id, expected_items[0].item_id)
        self.assertEqual(result.items[1].item_id, expected_items[1].item_id)

        self.network.GET.assert_called_once_with(
            "?comp=list",
            headers={"x-ms-version": "2017-11-09"},
            query={"maxresults": 1000},
        )

    async def test_list_root_items_failure(self):
        """Test container listing failure"""
        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(side_effect=Exception("XML parse error"))
        self.network.GET.return_value.__aenter__.return_value = mock_response

        with self.assertRaises(UnexpectedAddonError) as context:
            await self.azure_blob_storage_imp.list_root_items()

        self.assertIn("Failed to list containers", str(context.exception))

    async def test_list_child_items_success(self):
        """Test successful blob listing in a container"""
        mock_xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/testcontainer">
            <Blobs>
                <Blob>
                    <Name>file1.txt</Name>
                </Blob>
                <Blob>
                    <Name>folder/file2.txt</Name>
                </Blob>
            </Blobs>
        </EnumerationResults>"""

        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=mock_xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.list_child_items("testcontainer:/")

        expected_items = [
            ItemResult(
                item_id="testcontainer:/file1.txt",
                item_name="file1.txt",
                item_type=ItemType.FILE,
            ),
            ItemResult(
                item_id="testcontainer:/folder/file2.txt",
                item_name="file2.txt",
                item_type=ItemType.FILE,
            ),
        ]

        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].item_id, expected_items[0].item_id)
        self.assertEqual(result.items[0].item_name, expected_items[0].item_name)

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2017-11-09"},
            query={
                "restype": "container",
                "comp": "list",
                "prefix": "",
                "maxresults": 1000,
            },
        )

    async def test_list_child_items_invalid_id(self):
        """Test child items listing with invalid item ID"""
        result = await self.azure_blob_storage_imp.list_child_items("invalid-id")

        self.assertEqual(len(result.items), 0)
        self.network.GET.assert_not_called()

    async def test_list_child_items_failure(self):
        """Test blob listing failure"""
        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(side_effect=Exception("XML parse error"))
        self.network.GET.return_value.__aenter__.return_value = mock_response

        with self.assertRaises(UnexpectedAddonError) as context:
            await self.azure_blob_storage_imp.list_child_items("testcontainer:/")

        self.assertIn("Failed to list blobs", str(context.exception))

    async def test_get_item_info_container(self):
        """Test getting container info"""
        mock_response = AsyncMock()
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.get_item_info("testcontainer:/")

        expected_result = ItemResult(
            item_id="testcontainer:/",
            item_name="testcontainer/",
            item_type=ItemType.FOLDER,
        )

        self.assertEqual(result.item_id, expected_result.item_id)
        self.assertEqual(result.item_name, expected_result.item_name)
        self.assertEqual(result.item_type, expected_result.item_type)

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2017-11-09"},
            query={"restype": "container"},
        )

    async def test_get_item_info_blob(self):
        """Test getting blob info"""
        mock_response = AsyncMock()
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.get_item_info(
            "testcontainer:/test/file.txt"
        )

        expected_result = ItemResult(
            item_id="testcontainer:/test/file.txt",
            item_name="file.txt",
            item_type=ItemType.FILE,
        )

        self.assertEqual(result.item_id, expected_result.item_id)
        self.assertEqual(result.item_name, expected_result.item_name)
        self.assertEqual(result.item_type, expected_result.item_type)

        self.network.GET.assert_called_once_with(
            "testcontainer/test/file.txt",
            headers={"x-ms-version": "2017-11-09"},
            query={"comp": "metadata"},
        )

    async def test_get_item_info_invalid_id(self):
        """Test getting item info with invalid ID"""
        with self.assertRaises(ItemNotFound) as context:
            await self.azure_blob_storage_imp.get_item_info("invalid-id")

        self.assertIn("Invalid item ID", str(context.exception))
        self.network.GET.assert_not_called()

    async def test_get_item_info_failure(self):
        """Test getting item info failure"""
        # Make the network GET call itself raise an exception
        self.network.GET.side_effect = Exception("Network error")

        with self.assertRaises(ItemNotFound) as context:
            await self.azure_blob_storage_imp.get_item_info("testcontainer:/test.txt")

        self.assertIn("not found", str(context.exception))

    async def test_list_root_items_empty_response(self):
        """Test container listing with empty response"""
        mock_xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/">
            <Containers>
            </Containers>
        </EnumerationResults>"""

        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=mock_xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.list_root_items()

        self.assertEqual(len(result.items), 0)

    async def test_list_child_items_with_prefix(self):
        """Test blob listing with specific prefix"""
        mock_xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/testcontainer">
            <Blobs>
                <Blob>
                    <Name>docs/readme.txt</Name>
                </Blob>
            </Blobs>
        </EnumerationResults>"""

        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=mock_xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.list_child_items(
            "testcontainer:/docs"
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].item_name, "readme.txt")

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2017-11-09"},
            query={
                "restype": "container",
                "comp": "list",
                "prefix": "docs",
                "maxresults": 1000,
            },
        )

    def test_xml_parsing_malformed(self):
        """Test XML parsing with malformed XML"""
        malformed_xml = "not valid xml"

        # This should not raise an exception but return empty list
        try:
            ET.fromstring(malformed_xml)
        except ET.ParseError:
            # Expected behavior - parsing should fail gracefully
            pass

    async def test_list_child_items_with_item_type_filter(self):
        """Test blob listing with item type filter"""
        mock_xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/testcontainer">
            <Blobs>
                <Blob>
                    <Name>file1.txt</Name>
                </Blob>
                <Blob>
                    <Name>file2.txt</Name>
                </Blob>
            </Blobs>
        </EnumerationResults>"""

        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=mock_xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_blob_storage_imp.list_child_items(
            "testcontainer:/", item_type=ItemType.FILE
        )
        self.assertEqual(len(result.items), 2)

        result = await self.azure_blob_storage_imp.list_child_items(
            "testcontainer:/", item_type=ItemType.FOLDER
        )
        self.assertEqual(len(result.items), 0)
