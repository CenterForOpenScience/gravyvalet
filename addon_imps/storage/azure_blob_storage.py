import logging
import xml.etree.ElementTree as ET

from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.interfaces import storage


logger = logging.getLogger(__name__)


class AzureBlobStorageImp(storage.StorageAddonHttpRequestorImp):
    """Storage on Azure Blob Storage using REST API"""

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        """List containers using REST API"""
        try:
            async with self.network.GET(
                "?comp=list",
                headers={"x-ms-version": "2017-11-09"},
                query={"maxresults": 1000},
            ) as response:
                root = ET.fromstring(await response.text_content())
                containers = []
                for container in root.findall(".//Container"):
                    name_elem = container.find("Name")
                    if name_elem is not None:
                        containers.append(
                            storage.ItemResult(
                                item_id=f"{name_elem.text}:/",
                                item_name=f"{name_elem.text}/",
                                item_type=storage.ItemType.FOLDER,
                            )
                        )
                return storage.ItemSampleResult(items=containers)
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            raise UnexpectedAddonError("Failed to list containers")

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        """List blobs in a container"""
        if ":" not in item_id:
            return storage.ItemSampleResult(items=[])

        container_name, prefix = item_id.split(":/", 1)
        try:
            async with self.network.GET(
                f"{container_name}",
                headers={"x-ms-version": "2017-11-09"},
                query={
                    "restype": "container",
                    "comp": "list",
                    "prefix": prefix,
                    "maxresults": 1000,
                },
            ) as response:
                root = ET.fromstring(await response.text_content())
                items = []
                for blob in root.findall(".//Blob"):
                    name_elem = blob.find("Name")
                    if name_elem is not None:
                        item_result = storage.ItemResult(
                            item_id=f"{container_name}:/{name_elem.text}",
                            item_name=name_elem.text.split("/")[-1],
                            item_type=storage.ItemType.FILE,
                        )
                        # Apply item_type filter if specified
                        if item_type is None or item_result.item_type == item_type:
                            items.append(item_result)
                return storage.ItemSampleResult(items=items)
        except Exception as e:
            logger.error(f"Failed to list blobs: {str(e)}")
            raise UnexpectedAddonError("Failed to list blobs")

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        """Get information about container or blob"""
        if ":" not in item_id:
            raise ItemNotFound(f"Invalid item ID: {item_id}")

        container_name, blob_name = item_id.split(":/", 1)
        try:
            if not blob_name:  # Container
                async with self.network.GET(
                    f"{container_name}",
                    headers={"x-ms-version": "2017-11-09"},
                    query={"restype": "container"},
                ) as _:
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=f"{container_name}/",
                        item_type=storage.ItemType.FOLDER,
                    )
            else:  # Blob
                async with self.network.GET(
                    f"{container_name}/{blob_name}",
                    headers={"x-ms-version": "2017-11-09"},
                    query={"comp": "metadata"},
                ) as _:
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=blob_name.split("/")[-1],
                        item_type=storage.ItemType.FILE,
                    )
        except Exception as e:
            logger.error(f"Failed to get item info: {str(e)}")
            raise ItemNotFound(f"Item {item_id} not found")
