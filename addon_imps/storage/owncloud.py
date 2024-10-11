import base64
import functools
import typing
import xml.etree.ElementTree as ET
from urllib.parse import (
    unquote,
    urlparse,
)

from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import ItemType


def _get_basic_auth_header(username: str, password: str) -> str:
    credentials = f"{username}:{password}"
    return "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("utf-8")


class OwnCloudStorageImp(storage.StorageAddonHttpRequestorImp):
    """Storage implementation for ownCloud using WebDAV."""

    username = "username"
    password = "password"

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        headers = {
            "Depth": "0",
            "Authorization": _get_basic_auth_header(self.username, self.password),
        }
        async with self.network.request(
            http_method="PROPFIND",
            uri_path="",
            headers=headers,
            content=self._build_propfind_current_user_principal(),
        ) as response:
            response_xml = await response.text_content()
            current_user_principal_url = self._parse_current_user_principal(
                response_xml
            )

        # Remove leading slash to keep it relative
        if current_user_principal_url.startswith("/"):
            current_user_principal_url = current_user_principal_url.lstrip("/")

        async with self.network.request(
            http_method="PROPFIND",
            uri_path=current_user_principal_url,
            headers=headers,
            content=self._build_propfind_displayname(),
        ) as response:
            response_xml = await response.text_content()
            displayname = self._parse_displayname(response_xml)
            return displayname

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        # Adjusted to list child items of the root folder
        return await self.list_child_items(_owncloud_root_id(), page_cursor)

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        item_type, path = _parse_item_id(item_id)
        url = self._build_url(path)

        headers = {
            "Depth": "0",
            "Authorization": _get_basic_auth_header(self.username, self.password),
        }

        async with self.network.request(
            http_method="PROPFIND",
            uri_path=url,
            headers=headers,
            content=self._build_propfind_allprops(),
        ) as response:
            response_xml = await response.text_content()

            # For debugging: print the response XML
            print("Response XML in get_item_info:", response_xml)

            parsed_item = self._parse_item(response_xml, path)
            return parsed_item

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        _item_type, path = _parse_item_id(item_id)
        url = self._build_url(path)

        headers = {
            "Depth": "1",
            "Authorization": _get_basic_auth_header(self.username, self.password),
        }

        async with self.network.request(
            http_method="PROPFIND",
            uri_path=url,
            headers=headers,
            content=self._build_propfind_allprops(),
        ) as response:
            response_xml = await response.text_content()

            # For debugging: print the response XML
            print("Response XML in list_child_items:", response_xml)

            parsed_items = self._parse_items(
                response_xml, base_path=path, item_type=item_type
            )
            return storage.ItemSampleResult(
                items=list(parsed_items),
            )

    def _build_url(self, path: str) -> str:
        if path == "/":
            return ""  # Root path
        else:
            return f"{path.lstrip('/')}"

    def _build_propfind_current_user_principal(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
    <d:prop>
        <d:current-user-principal/>
    </d:prop>
</d:propfind>"""

    def _build_propfind_displayname(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
    <d:prop>
        <d:displayname/>
    </d:prop>
</d:propfind>"""

    def _build_propfind_allprops(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
    <d:allprop/>
</d:propfind>"""

    def _parse_current_user_principal(self, response_xml: str) -> str:
        ns = {"d": "DAV:"}
        root = ET.fromstring(response_xml)
        current_user_principal = root.find(".//d:current-user-principal/d:href", ns)
        if current_user_principal is not None and current_user_principal.text:
            return current_user_principal.text
        else:
            raise ValueError("current-user-principal not found in response")

    def _parse_displayname(self, response_xml: str) -> str:
        ns = {"d": "DAV:"}
        root = ET.fromstring(response_xml)
        displayname = root.find(".//d:displayname", ns)
        if displayname is not None and displayname.text:
            return displayname.text
        else:
            raise ValueError("displayname not found in response")

    def _parse_item(self, response_xml: str, path: str) -> storage.ItemResult:
        ns = {"d": "DAV:", "oc": "http://owncloud.org/ns"}
        root = ET.fromstring(response_xml)
        response_element = root.find("d:response", ns)
        if response_element is None:
            raise ValueError("No response element found in PROPFIND response")

        resourcetype = response_element.find(".//d:resourcetype", ns)
        if (
            resourcetype is not None
            and resourcetype.find("d:collection", ns) is not None
        ):
            item_type = storage.ItemType.FOLDER
        else:
            item_type = storage.ItemType.FILE

        displayname_element = response_element.find(".//d:displayname", ns)
        if displayname_element is not None and displayname_element.text:
            displayname = displayname_element.text
        else:
            displayname = path.rstrip("/").split("/")[-1]

        item_result = storage.ItemResult(
            item_id=_make_item_id(item_type, path),
            item_name=displayname,
            item_type=item_type,
        )
        return item_result

    def _parse_items(
        self,
        response_xml: str,
        base_path: str,
        item_type: storage.ItemType | None = None,
    ) -> typing.Iterator[storage.ItemResult]:
        ns = {"d": "DAV:", "oc": "http://owncloud.org/ns"}
        root = ET.fromstring(response_xml)
        for response_element in root.findall("d:response", ns):
            href_element = response_element.find("d:href", ns)
            if href_element is None or not href_element.text:
                continue
            href = href_element.text
            path = self._href_to_path(href)

            if path.rstrip("/") == base_path.rstrip("/"):
                continue

            resourcetype = response_element.find(".//d:resourcetype", ns)
            if (
                resourcetype is not None
                and resourcetype.find("d:collection", ns) is not None
            ):
                _item_type = storage.ItemType.FOLDER
            else:
                _item_type = storage.ItemType.FILE

            if item_type is not None and _item_type != item_type:
                continue

            displayname_element = response_element.find(".//d:displayname", ns)
            if displayname_element is not None and displayname_element.text:
                displayname = displayname_element.text
            else:
                displayname = path.rstrip("/").split("/")[-1]

            yield storage.ItemResult(
                item_id=_make_item_id(_item_type, path),
                item_name=displayname,
                item_type=_item_type,
            )

    def _href_to_path(self, href: str) -> str:
        parsed_href = urlparse(unquote(href))
        href_path = parsed_href.path.lstrip("/")

        base_path = urlparse(self.config.external_api_url).path.rstrip("/").lstrip("/")
        if href_path.startswith(base_path):
            # fmt: off
            path = href_path[len(base_path):]
        else:
            path = href_path
        return path or "/"


###
# Module-local helpers


def _make_item_id(item_type: storage.ItemType, path: str) -> str:
    return f"{item_type.value}:{path}"


def _parse_item_id(item_id: str) -> tuple[storage.ItemType, str]:
    try:
        if not item_id:
            return ItemType.FOLDER, "/"
        (_type, _path) = item_id.split(":", maxsplit=1)
        return (storage.ItemType(_type), _path)
    except ValueError:
        raise ValueError(
            f'Expected id of format "type:path", e.g. "FOLDER:/path/to/folder" (got "{item_id}")'
        )


@functools.cache
def _owncloud_root_id() -> str:
    return _make_item_id(storage.ItemType.FOLDER, "/")
