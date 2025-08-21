import unittest
from typing import Optional
from unittest.mock import AsyncMock

from addon_imps.storage.azure_blob_storage import AzureBlobStorageImp
from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.interfaces.storage import (
    ItemType,
    StorageConfig,
)


class TestAzureBlobStorageImp(unittest.IsolatedAsyncioTestCase):
    """Test suite for Azure Blob Storage implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = StorageConfig(
            external_api_url="https://teststorage.blob.core.windows.net",
            connected_root_id="testcontainer",
            external_account_id="teststorage",
            max_upload_mb=100,
        )
        self.network = AsyncMock(spec=HttpRequestor)
        self.azure_imp = AzureBlobStorageImp(config=self.config, network=self.network)

    def _create_mock_response(self, xml_content: str) -> AsyncMock:
        """Helper to create mock HTTP response"""
        mock_response = AsyncMock()
        mock_response.text_content = AsyncMock(return_value=xml_content)
        return mock_response

    def _create_containers_xml(self, container_names: list[str]) -> str:
        """Helper to create containers XML response"""
        containers_xml = ""
        for name in container_names:
            containers_xml += f"<Container><Name>{name}</Name></Container>"

        return f"""<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/">
            <Containers>{containers_xml}</Containers>
        </EnumerationResults>"""

    def _create_blobs_xml(
        self,
        blobs: Optional[list[str]] = None,
        blob_prefixes: Optional[list[str]] = None,
    ) -> str:
        """Helper to create blobs XML response"""
        blobs_xml = ""

        if blob_prefixes:
            for prefix in blob_prefixes:
                blobs_xml += f"<BlobPrefix><Name>{prefix}</Name></BlobPrefix>"

        if blobs:
            for blob in blobs:
                blobs_xml += f"<Blob><Name>{blob}</Name></Blob>"

        return f"""<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/testcontainer">
            <Blobs>{blobs_xml}</Blobs>
        </EnumerationResults>"""

    async def test_get_external_account_id_from_valid_url(self):
        """Test extracting account ID from valid Azure URL"""
        result = await self.azure_imp.get_external_account_id({})
        self.assertEqual(result, "teststorage")

    async def test_get_external_account_id_from_empty_url(self):
        """Test handling empty API URL"""
        self.azure_imp.config = StorageConfig(external_api_url="", max_upload_mb=100)
        result = await self.azure_imp.get_external_account_id({})
        self.assertEqual(result, "")

    async def test_build_wb_config_basic(self):
        """Test basic WaterButler config building"""
        result = await self.azure_imp.build_wb_config()
        expected = {
            "account_name": "teststorage",
            "container": "testcontainer",
            "base_folder": "",
        }
        self.assertEqual(result, expected)

    async def test_build_wb_config_with_subfolder(self):
        """Test WaterButler config with subfolder"""
        self.azure_imp.config = StorageConfig(
            external_api_url="https://teststorage.blob.core.windows.net",
            connected_root_id="testcontainer:/subfolder",
            external_account_id="teststorage",
            max_upload_mb=100,
        )
        result = await self.azure_imp.build_wb_config()
        expected = {
            "account_name": "teststorage",
            "container": "testcontainer",
            "base_folder": "subfolder",
        }
        self.assertEqual(result, expected)

    def test_api_version_consistency(self):
        """Test API version is consistent across methods"""
        self.assertEqual(self.azure_imp.API_VERSION, "2025-07-05")
        headers = self.azure_imp.api_headers
        self.assertEqual(headers["x-ms-version"], "2025-07-05")

    async def test_list_root_items_success(self):
        """Test successful listing of containers"""
        xml_response = self._create_containers_xml(["container1", "container2"])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_root_items()

        self.assertEqual(len(result.items), 2)
        self.assertEqual(list(result.items)[0].item_id, "container1:/")
        self.assertEqual(list(result.items)[1].item_id, "container2:/")

        self.network.GET.assert_called_once_with(
            "?comp=list",
            headers={"x-ms-version": "2025-07-05"},
            query={"maxresults": 1000},
        )

    async def test_list_root_items_empty(self):
        """Test listing containers when none exist"""
        xml_response = self._create_containers_xml([])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_root_items()
        self.assertEqual(len(result.items), 0)

    async def test_list_root_items_network_error(self):
        """Test network error during container listing"""
        self.network.GET.return_value.__aenter__.side_effect = Exception(
            "Network error"
        )

        with self.assertRaises(UnexpectedAddonError) as context:
            await self.azure_imp.list_root_items()

        self.assertIn("Failed to list containers", str(context.exception))

    async def test_list_child_items_files_only(self):
        """Test listing files in container root"""
        xml_response = self._create_blobs_xml(blobs=["file1.txt", "file2.txt"])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_child_items("testcontainer:/")

        self.assertEqual(len(result.items), 2)
        self.assertEqual(list(result.items)[0].item_name, "file1.txt")
        self.assertEqual(list(result.items)[0].item_type, ItemType.FILE)

    async def test_list_child_items_with_folders(self):
        """Test listing items including folders (BlobPrefix)"""
        xml_response = self._create_blobs_xml(
            blobs=["file1.txt"], blob_prefixes=["docs/"]
        )
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_child_items("testcontainer:/")

        self.assertEqual(len(result.items), 2)

        folder_item = next(
            (item for item in result.items if item.item_type == ItemType.FOLDER), None
        )
        self.assertIsNotNone(folder_item)
        self.assertEqual(folder_item.item_name, "docs/")

    async def test_list_child_items_with_filter(self):
        """Test listing with item type filter"""
        xml_response = self._create_blobs_xml(
            blobs=["file1.txt"], blob_prefixes=["docs/"]
        )
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_child_items(
            "testcontainer:/", item_type=ItemType.FOLDER
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(list(result.items)[0].item_type, ItemType.FOLDER)

    async def test_list_child_items_basic_validation(self):
        """Test basic validation for list_child_items"""
        with self.assertRaises(ValueError) as context:
            result = await self.azure_imp.list_child_items("")
        self.assertIn("Empty item_id provided", str(context.exception))
        self.network.GET.assert_not_called()

        self.network.reset_mock()

        xml_response = self._create_blobs_xml(blobs=[])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_child_items("just-container-name")
        self.assertEqual(len(result.items), 0)

        self.network.GET.assert_called_once_with(
            "just-container-name",
            headers={"x-ms-version": "2025-07-05"},
            query={
                "restype": "container",
                "comp": "list",
                "maxresults": 1000,
                "delimiter": "/",
            },
        )

    async def test_list_child_items_network_error(self):
        """Test network error during child items listing"""
        self.network.GET.return_value.__aenter__.side_effect = Exception(
            "Network error"
        )

        with self.assertRaises(UnexpectedAddonError) as context:
            await self.azure_imp.list_child_items("testcontainer:/")

        self.assertIn("Failed to list blobs", str(context.exception))

    async def test_get_item_info_container(self):
        """Test getting container info"""
        mock_response = AsyncMock()
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.get_item_info("testcontainer")

        self.assertEqual(result.item_name, "testcontainer")
        self.assertEqual(result.item_type, ItemType.FOLDER)

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2025-07-05"},
            query={"restype": "container"},
        )

    async def test_get_item_info_blob(self):
        """Test getting blob info"""
        mock_response = AsyncMock()
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.get_item_info("testcontainer:/docs/file.txt")

        self.assertEqual(result.item_name, "file.txt")
        self.assertEqual(result.item_type, ItemType.FILE)

        self.network.GET.assert_called_once_with(
            "testcontainer/docs/file.txt",
            headers={"x-ms-version": "2025-07-05"},
            query={"comp": "metadata"},
        )

    async def test_get_item_info_various_formats(self):
        """Test that various item ID formats are accepted"""
        mock_response = AsyncMock()
        self.network.GET.return_value.__aenter__.return_value = mock_response

        test_cases = [
            ("container", "container", ItemType.FOLDER),
            ("test-container", "test-container", ItemType.FOLDER),
            ("testcontainer:/file.txt", "file.txt", ItemType.FILE),
            ("container-123:/docs/file.pdf", "file.pdf", ItemType.FILE),
        ]

        for item_id, expected_name, expected_type in test_cases:
            with self.subTest(item_id=item_id):
                result = await self.azure_imp.get_item_info(item_id)
                self.assertEqual(result.item_name, expected_name)
                self.assertEqual(result.item_type, expected_type)

    async def test_get_item_info_network_error(self):
        """Test network error during item info retrieval"""
        self.network.GET.return_value.__aenter__.side_effect = Exception(
            "Network error"
        )

        with self.assertRaises(ItemNotFound):
            await self.azure_imp.get_item_info("testcontainer:/file.txt")

    async def test_parse_containers_with_empty_names(self):
        """Test parsing containers XML with empty names"""
        xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/">
            <Containers>
                <Container><Name>validcontainer</Name></Container>
                <Container><Name></Name></Container>
                <Container></Container>
            </Containers>
        </EnumerationResults>"""

        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_root_items()

        self.assertEqual(len(result.items), 1)
        self.assertEqual(list(result.items)[0].item_name, "validcontainer/")

    async def test_parse_blobs_with_mixed_content(self):
        """Test parsing blobs XML with mixed valid and invalid content"""
        xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <EnumerationResults ServiceEndpoint="https://teststorage.blob.core.windows.net/testcontainer">
            <Blobs>
                <BlobPrefix><Name>docs/</Name></BlobPrefix>
                <BlobPrefix><Name></Name></BlobPrefix>
                <Blob><Name>file1.txt</Name></Blob>
                <Blob><Name></Name></Blob>
                <Blob></Blob>
            </Blobs>
        </EnumerationResults>"""

        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        result = await self.azure_imp.list_child_items("testcontainer:/")

        self.assertEqual(len(result.items), 2)

    async def test_list_child_items_query_parameters(self):
        """Test that correct query parameters are sent for child item listing"""
        xml_response = self._create_blobs_xml([])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        await self.azure_imp.list_child_items("testcontainer:/docs/")

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2025-07-05"},
            query={
                "restype": "container",
                "comp": "list",
                "prefix": "docs/",
                "maxresults": 1000,
                "delimiter": "/",
            },
        )

    async def test_list_child_items_root_prefix(self):
        """Test listing child items in container root (empty prefix)"""
        xml_response = self._create_blobs_xml(blobs=["file1.txt"])
        mock_response = self._create_mock_response(xml_response)
        self.network.GET.return_value.__aenter__.return_value = mock_response

        await self.azure_imp.list_child_items(
            "testcontainer:/base_folder", item_type=None
        )

        self.network.GET.assert_called_once_with(
            "testcontainer",
            headers={"x-ms-version": "2025-07-05"},
            query={
                "restype": "container",
                "comp": "list",
                "prefix": "base_folder",
                "maxresults": 1000,
                "delimiter": "/",
            },
        )

    async def test_parse_item_id_validation(self):
        """Test item ID parsing validation"""
        # Test valid formats
        container, path = self.azure_imp._parse_item_id("testcontainer")
        self.assertEqual(container, "testcontainer")
        self.assertEqual(path, "")

        container, path = self.azure_imp._parse_item_id("testcontainer:/")
        self.assertEqual(container, "testcontainer")
        self.assertEqual(path, "")

        container, path = self.azure_imp._parse_item_id("testcontainer:/docs/file.txt")
        self.assertEqual(container, "testcontainer")
        self.assertEqual(path, "docs/file.txt")

        # Test invalid formats that should raise ValueError
        with self.assertRaises(ValueError) as context:
            self.azure_imp._parse_item_id("")
        self.assertIn("Empty item_id provided", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.azure_imp._parse_item_id(":/path")
        self.assertIn("Invalid item_id format", str(context.exception))

        with self.assertRaises(ValueError) as context:
            self.azure_imp._parse_item_id("container:path")
        self.assertIn("Invalid item_id format", str(context.exception))

    async def test_get_item_info_invalid_formats(self):
        """Test that get_item_info properly handles invalid item ID formats"""
        invalid_formats = [
            ":/invalid",
            "container:invalid-path",
            ":container:/path",
        ]

        for invalid_id in invalid_formats:
            with self.subTest(item_id=invalid_id):
                with self.assertRaises(ValueError):
                    await self.azure_imp.get_item_info(invalid_id)
