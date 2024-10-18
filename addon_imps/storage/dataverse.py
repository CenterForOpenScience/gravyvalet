from __future__ import annotations

import asyncio
import re
from dataclasses import (
    dataclass,
    fields,
)

from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


DATAVERSE_REGEX = re.compile(r"^dataverse/(?P<id>\d*)$")
DATASET_REGEX = re.compile(r"^dataset/(?P<id>\d*)$")
FILE_REGEX = re.compile(r"^file/(?P<id>\d*)$")


@dataclass
class DataverseStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on dataverse

    see https://guides.dataverse.org/en/latest/api/native-api.html
    """

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        return ""

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        async with self.network.GET(
            "mydata/retrieve",
            query=[
                ["page", page_cursor],
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
            ],
        ) as response:
            content = await response.json_content()
            return parse_mydata(content["data"])

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if not item_id:
            return ItemResult(item_id="", item_name="", item_type=ItemType.FOLDER)
        elif match := DATAVERSE_REGEX.match(item_id):
            entity = await self._fetch_dataverse(match["id"])
        elif match := DATASET_REGEX.match(item_id):
            entity = await self._fetch_dataset(match["id"])
        elif match := FILE_REGEX.match(item_id):
            entity = await self._fetch_file(match["id"])
        else:
            raise ValueError(f"Invalid item id: {item_id}")

        return entity

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        if not item_id:
            return await self.list_root_items(page_cursor)
        elif item_type != ItemType.FILE and (match := DATAVERSE_REGEX.match(item_id)):
            items = await self._fetch_dataverse_items(match["id"])
            return storage.ItemSampleResult(
                items=items,
                total_count=len(items),
            )
        elif item_type != ItemType.FOLDER and (match := DATASET_REGEX.match(item_id)):
            items = await self._fetch_dataset_files(match["id"])
            return storage.ItemSampleResult(
                items=items,
                total_count=len(items),
            )
        else:
            return ItemSampleResult(items=[], total_count=0)

    async def _fetch_dataverse_items(self, dataverse_id) -> list[ItemResult]:
        async with self.network.GET(f"dataverses/{dataverse_id}/contents") as response:
            response_content = await response.json_content()
            return await asyncio.gather(
                *[
                    self.get_dataverse_or_dataset_item(item)
                    for item in response_content["data"]
                ]
            )

    async def get_dataverse_or_dataset_item(self, item: dict):
        match item["type"]:
            case "dataset":
                return await self._fetch_dataset(item["id"])
            case "dataverse":
                return parse_dataverse_as_subitem(item)
        raise ValueError(f"Invalid item type: {item['type']}")

    async def _fetch_dataverse(self, dataverse_id) -> ItemResult:
        async with self.network.GET(f"dataverses/{dataverse_id}") as response:
            return parse_dataverse(await response.json_content())

    async def _fetch_dataset(self, dataset_id: str) -> ItemResult:
        async with self.network.GET(f"datasets/{dataset_id}") as response:
            return parse_dataset(await response.json_content())

    async def _fetch_dataset_files(self, dataset_id) -> list[ItemResult]:
        async with self.network.GET(f"datasets/{dataset_id}") as response:
            return parse_dataset_files(await response.json_content())

    async def _fetch_file(self, dataverse_id) -> ItemResult:
        async with self.network.GET(f"files/{dataverse_id}") as response:
            return parse_datafile(await response.json_content())


###
# module-local helpers


def parse_dataverse_as_subitem(data: dict):
    return ItemResult(
        item_type=ItemType.FOLDER,
        item_name=data["title"],
        item_id=f'dataverse/{data["id"]}',
    )


def parse_datafile(data: dict):
    if data.get("data"):
        data = data["data"]

    return ItemResult(
        item_type=ItemType.FILE,
        item_name=data["label"],
        item_id=f'file/{data['dataFile']["id"]}',
    )


def parse_dataverse(data: dict):
    if data.get("data"):
        data = data["data"]
    return ItemResult(
        item_type=ItemType.FOLDER,
        item_name=data["name"],
        item_id=f'dataverse/{data["id"]}',
    )


def parse_mydata(data: dict):
    if data.get("data"):
        data = data["data"]
    return ItemSampleResult(
        items=[
            ItemResult(
                item_id=f"dataverse/{file['entity_id']}",
                item_name=file["name"],
                item_type=ItemType.FOLDER,
            )
            for file in data["items"]
        ],
        total_count=data["total_count"],
        next_sample_cursor=data["pagination"]["nextPageNumber"],
    )


@dataclass(frozen=True, slots=True)
class Dataverse:
    name: str
    id: str
    type: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"{self.type}/{self.id}",
            item_name=self.name,
            item_type=self.item_type,
        )

    @property
    def item_type(self) -> ItemType:
        if self.type == "datafile":
            return ItemType.FILE
        else:
            return ItemType.FOLDER

    @classmethod
    def from_json(cls, json: dict):
        return cls(**{key.name: json.get(key.name, key.default) for key in fields(cls)})


def parse_dataset(data: dict) -> ItemResult:
    if data.get("data"):
        data = data["data"]
    try:
        return ItemResult(
            item_id=f'dataset/{data["id"]}',
            item_name=[
                item
                for item in data["latestVersion"]["metadataBlocks"]["citation"][
                    "fields"
                ]
                if item["typeName"] == "title"
            ][0]["value"],
            item_type=ItemType.FOLDER,
        )
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid dataset response: {e=}")


def parse_dataset_files(data: dict) -> list[ItemResult]:
    if data.get("data"):
        data = data["data"]
    try:
        return [
            ItemResult(
                item_id=f"file/{file['dataFile']['id']}",
                item_name=file["label"],
                item_type=ItemType.FILE,
            )
            for file in data["latestVersion"]["files"]
        ]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid dataset response:{e=}")
