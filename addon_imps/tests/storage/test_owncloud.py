import unittest
from unittest.mock import (
    AsyncMock,
    sentinel,
)

from addon_imps.storage.owncloud import (
    _BUILD_PROPFIND_ALLPROPS,
    _BUILD_PROPFIND_CURRENT_USER_PRINCIPAL,
    OwnCloudStorageImp,
)
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class TestOwnCloudStorageImp(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.base_url = "https://owncloud-api.com"
        self.config = storage.StorageConfig(
            external_api_url=self.base_url, max_upload_mb=123
        )
        self.network = AsyncMock(spec_set=storage.HttpRequestor)
        self.imp = OwnCloudStorageImp(config=self.config, network=self.network)

    def _patch_request(self, return_value: str):
        mock = self.network.PROPFIND.return_value.__aenter__.return_value
        mock.text_content = AsyncMock(return_value=return_value)
        mock.http_status = 200

    def _assert_request(self, url: str, headers: dict, content: str):
        self.network.PROPFIND.assert_called_once_with(
            uri_path=url,
            headers=headers,
            content=content,
        )
        self.network.PROPFIND.return_value.__aenter__.assert_awaited_once_with()
        self.network.PROPFIND.return_value.__aenter__.return_value.text_content.assert_awaited_once_with()
        self.network.PROPFIND.return_value.__aexit__.assert_awaited_once_with(
            None, None, None
        )

    async def test_get_external_account_id(self):
        response_xml = """<?xml version="1.0" encoding="utf-8"?>
        <d:multistatus xmlns:d="DAV:">
            <d:response>
                <d:href>/remote.php/dav/principals/users/username/</d:href>
                <d:propstat>
                    <d:prop>
                        <d:current-user-principal>
                            <d:href>/remote.php/dav/principals/users/username/</d:href>
                        </d:current-user-principal>
                    </d:prop>
                    <d:status>HTTP/1.1 200 OK</d:status>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        self._patch_request(response_xml)
        displayname_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <d:multistatus xmlns:d="DAV:">
            <d:response>
                <d:href>/users/username/</d:href>
                <d:propstat>
                    <d:status>HTTP/1.1 200 OK</d:status>
                    <d:prop>
                        <d:current-user-principal>
                            <d:href>/remote.php/dav/principals/users/username/</d:href>
                        </d:current-user-principal>
                        <d:displayname>Test User</d:displayname>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        self._patch_request(displayname_xml)

        result = await self.imp.get_external_account_id({})

        self.assertEqual(result, "Test User")
        self._assert_request(
            "",
            {"Depth": "0"},
            _BUILD_PROPFIND_CURRENT_USER_PRINCIPAL,
        )

    async def test_list_root_items(self):
        # Mock the list_child_items call since it's used by list_root_items
        mock_response = sentinel.result
        self.imp.list_child_items = AsyncMock(return_value=mock_response)

        # Call the method
        result = await self.imp.list_root_items()

        # Assert the result and list_child_items call
        self.assertEqual(result, mock_response)
        self.imp.list_child_items.assert_awaited_once_with("FOLDER:/", "")

    async def test_get_item_info(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <d:multistatus xmlns:d="DAV:">
            <d:response>
                <d:href>/remote.php/webdav/test-folder/</d:href>
                <d:propstat>
                    <d:status>HTTP/1.1 200 OK</d:status>
                    <d:prop>
                        <d:displayname>test-folder</d:displayname>
                        <d:resourcetype><d:collection/></d:resourcetype>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        self._patch_request(response_xml)

        # Call the method
        result = await self.imp.get_item_info("FOLDER:/test-folder")

        # Define the expected result
        expected_result = ItemResult(
            item_id="FOLDER:/test-folder",
            item_name="test-folder",
            item_type=ItemType.FOLDER,
        )

        # Assert the result and request
        self.assertEqual(result, expected_result)
        self._assert_request(
            "test-folder",
            {"Depth": "0"},
            _BUILD_PROPFIND_ALLPROPS,
        )

    async def test_list_child_items(self):
        response_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <d:multistatus xmlns:d="DAV:">
            <d:response>
                <d:href>/remote.php/webdav/test-folder/</d:href>
                <d:propstat>
                    <d:status>HTTP/1.1 200 OK</d:status>
                    <d:prop>
                        <d:displayname>test-folder</d:displayname>
                        <d:resourcetype><d:collection/></d:resourcetype>
                    </d:prop>
                </d:propstat>
            </d:response>
            <d:response>
                <d:href>/remote.php/webdav/test-file.txt</d:href>
                <d:propstat>
                    <d:status>HTTP/1.1 200 OK</d:status>
                    <d:prop>
                        <d:displayname>test-file.txt</d:displayname>
                        <d:resourcetype/>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        self._patch_request(response_xml)

        # Call the method
        result = await self.imp.list_child_items("FOLDER:/test-folder")

        # Define expected items
        expected_items = [
            ItemResult(
                item_id="FOLDER:/test-folder",
                item_name="test-folder",
                item_type=ItemType.FOLDER,
            ),
            ItemResult(
                item_id="FILE:/test-file.txt",
                item_name="test-file.txt",
                item_type=ItemType.FILE,
            ),
        ]
        expected_result = ItemSampleResult(items=expected_items)

        # Assert the result and request
        self.assertEqual(result.items, expected_result.items)
        self._assert_request(
            "test-folder",
            {"Depth": "1"},
            _BUILD_PROPFIND_ALLPROPS,
        )
