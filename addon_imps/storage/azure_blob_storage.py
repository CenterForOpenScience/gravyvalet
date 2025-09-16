import logging
import xml.etree.ElementTree as ET
from typing import Optional

from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.interfaces import storage


logger = logging.getLogger(__name__)


class AzureBlobStorageImp(storage.StorageAddonHttpRequestorImp):
    """Storage on Azure Blob Storage

    see https://docs.microsoft.com/en-us/rest/api/storageservices/blob-service-rest-api
    and https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-provider-aad?tabs=workforce-configuration
    """

    API_VERSION = "2025-07-05"
    MAX_RESULTS = 1000

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        if not self.config.external_api_url:
            return ""

        try:
            url_parts = self.config.external_api_url.replace("https://", "").split(".")
            if (
                len(url_parts) >= 4
                and url_parts[1:4] == ["blob", "core", "windows"]
                and url_parts[0]
            ):
                return url_parts[0]
        except Exception:
            logger.error("Failed to parse external API URL for Azure Blob Storage")
        return ""

    async def build_wb_config(self) -> dict:
        root_parts = self.config.connected_root_id.split(":/")
        return {
            "account_name": self.config.external_account_id,
            "container": root_parts[0],
            "base_folder": root_parts[1] if len(root_parts) > 1 else "",
        }

    @property
    def api_headers(self) -> dict[str, str]:
        return {"x-ms-version": self.API_VERSION}

    def _parse_containers(self, xml_root: ET.Element) -> list[storage.ItemResult]:
        containers = []
        for container in xml_root.findall(".//Container"):
            name_elem = container.find("Name")
            if name_elem is not None and name_elem.text:
                containers.append(
                    storage.ItemResult(
                        item_id=f"{name_elem.text}:/",
                        item_name=f"{name_elem.text}/",
                        item_type=storage.ItemType.FOLDER,
                    )
                )
        return containers

    def _parse_blob_items(
        self,
        xml_root: ET.Element,
        container_name: str,
        prefix: str,
        item_type: Optional[storage.ItemType],
    ) -> list[storage.ItemResult]:
        items = []

        for blob_prefix in xml_root.findall(".//BlobPrefix"):
            name_elem = blob_prefix.find("Name")
            if name_elem is not None and name_elem.text:
                folder_path = name_elem.text
                folder_name = folder_path.rstrip("/").split("/")[-1]
                item_result = storage.ItemResult(
                    item_id=f"{container_name}:/{folder_path}",
                    item_name=f"{folder_name}/",
                    item_type=storage.ItemType.FOLDER,
                )
                if item_type is None or item_result.item_type == item_type:
                    items.append(item_result)

        for blob in xml_root.findall(".//Blob"):
            name_elem = blob.find("Name")
            if name_elem is not None and name_elem.text:
                blob_name = name_elem.text

                if prefix:
                    if not blob_name.startswith(prefix):
                        continue
                    relative_name = blob_name.removeprefix(prefix)
                else:
                    relative_name = blob_name

                if "/" not in relative_name:
                    item_result = storage.ItemResult(
                        item_id=f"{container_name}:/{blob_name}",
                        item_name=relative_name,
                        item_type=storage.ItemType.FILE,
                    )
                    if item_type is None or item_result.item_type == item_type:
                        items.append(item_result)
        return items

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        try:
            async with self.network.GET(
                "?comp=list",
                headers=self.api_headers,
                query={"maxresults": self.MAX_RESULTS},
            ) as response:
                xml_root = ET.fromstring(await response.text_content())
                return storage.ItemSampleResult(items=self._parse_containers(xml_root))
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            raise UnexpectedAddonError("Failed to list containers")

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: Optional[storage.ItemType] = None,
    ) -> storage.ItemSampleResult:
        container_name, prefix = self._parse_item_id(item_id)

        query_params = {
            "restype": "container",
            "comp": "list",
            "maxresults": self.MAX_RESULTS,
            "delimiter": "/",
        }
        if prefix:
            query_params["prefix"] = prefix

        try:
            async with self.network.GET(
                container_name,
                headers=self.api_headers,
                query=query_params,
            ) as response:
                xml_root = ET.fromstring(await response.text_content())
                items = self._parse_blob_items(
                    xml_root, container_name, prefix, item_type
                )
                return storage.ItemSampleResult(items=items)
        except Exception as e:
            logger.error(f"Failed to list blobs in {item_id}: {str(e)}")
            raise UnexpectedAddonError("Failed to list blobs")

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        container_name, path = self._parse_item_id(item_id)

        try:
            if not path:
                async with self.network.GET(
                    container_name,
                    headers=self.api_headers,
                    query={"restype": "container"},
                ) as _:
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=container_name,
                        item_type=storage.ItemType.FOLDER,
                    )
            else:
                async with self.network.GET(
                    f"{container_name}/{path}",
                    headers=self.api_headers,
                    query={"comp": "metadata"},
                ) as _:
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=path.split("/")[-1],
                        item_type=storage.ItemType.FILE,
                    )
        except Exception as e:
            logger.error(f"Failed to get item info for {item_id}: {str(e)}")
            raise ItemNotFound(f"Item {item_id} not found")

    def _parse_item_id(self, item_id: str) -> tuple[str, str]:
        """
        Parse Azure Blob Storage item ID and return container name and path.

        Formats: 'container' or 'container:/path'
        Returns: (container_name, path)
        """
        if not item_id:
            raise ValueError(
                "Empty item_id provided. Expected 'container' or 'container:/path'"
            )

        if ":" in item_id:
            container_name, path_part = item_id.split(":", maxsplit=1)
            if not container_name or not path_part.startswith("/"):
                raise ValueError(
                    f"Invalid item_id format: {item_id}. Expected 'container' or 'container:/path'"
                )
            return (container_name, path_part.lstrip("/"))
        else:
            return (item_id, "")
