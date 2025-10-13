from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from http import HTTPStatus
from typing import Literal

from django.core.exceptions import ValidationError

from addon_toolkit.interfaces.link import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    LinkAddonHttpRequestorImp,
)


DATAVERSE_REGEX = re.compile(r"^dataverse/(?P<id_>.*)$")
DATASET_REGEX = re.compile(r"^dataset/(?P<persistent_id>.*)$")
FILE_REGEX = re.compile(r"^file/(?P<persistent_id>.*)$")


@dataclass
class DataverseLinkImp(LinkAddonHttpRequestorImp):
    """storage on dataverse

    see https://guides.dataverse.org/en/latest/api/native-api.html
    """

    async def build_url_for_id(self, item_id: str) -> str:
        if match := DATAVERSE_REGEX.match(item_id):
            entity_type = "dataverse"
        elif match := DATASET_REGEX.match(item_id):
            entity_type = "dataset"
        elif match := FILE_REGEX.match(item_id):
            entity_type = "file"
        else:
            raise ValidationError(f"Invalid {item_id=}")

        return self._make_url(entity_type, **match.groupdict())

    def _make_url(
        self,
        entity_type: Literal["file", "dataset", "dataverse"],
        persistent_id: str = None,
        id_: str = None,
    ):
        if bool(id_) == bool(persistent_id):
            raise ValueError("You must pass either id or persistent_id to build url")

        if persistent_id:
            suffix = f".xhtml?persistentId={persistent_id}"
        else:
            suffix = f"/{id_}"
        return f"{self.config.external_web_url}/{entity_type}{suffix}"

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        try:
            async with self.network.GET("api/v1/users/:me") as response:
                if not response.http_status.is_success:
                    raise ValidationError(
                        "Could not get dataverse account id, check your API Token"
                    )
                content = await response.json_content()
                return content.get("data", {}).get("id")
        except ValueError as exc:
            if "relative url may not alter the base url" in str(exc).lower():
                raise ValidationError(
                    "Invalid host URL. Please check your Dataverse base URL."
                )
            raise

    async def list_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        async with self.network.GET(
            "api/mydata/retrieve",
            query=[
                ["selected_page", page_cursor],
                *[("role_ids", role) for role in range(1, 9)],
                (
                    "dvobject_types",
                    "Dataverse",
                ),  # only published dataverses may contain published datasets
                ("published_states", "Published"),
            ],
        ) as response:
            content = await response.json_content()
            if resp_data := content.get("data"):
                return parse_mydata(resp_data)
            return ItemSampleResult(items=[], total_count=0)

    async def get_item_info(self, item_id: str) -> ItemResult:
        if not item_id:
            return ItemResult(item_id="", item_name="", item_type=ItemType.FOLDER)
        elif match := DATAVERSE_REGEX.match(item_id):
            entity = await self._fetch_dataverse(match["id_"])
        elif match := DATASET_REGEX.match(item_id):
            entity = await self._fetch_dataset(persistent_id=match["persistent_id"])
        elif match := FILE_REGEX.match(item_id):
            entity = await self._fetch_file(match["persistent_id"])
        else:
            raise ValueError(f"Invalid item id: {item_id}")

        return entity

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: ItemType | None = None,
    ) -> ItemSampleResult:
        if not item_id:
            return await self.list_root_items(page_cursor)
        elif match := DATAVERSE_REGEX.match(item_id):
            items = await self._fetch_dataverse_items(match["id_"])
            return ItemSampleResult(
                items=items,
                total_count=len(items),
            )
        elif match := DATASET_REGEX.match(item_id):
            items = await self._fetch_dataset_files(
                persistent_id=match["persistent_id"]
            )
            return ItemSampleResult(
                items=items,
                total_count=len(items),
            )
        else:
            return ItemSampleResult(items=[], total_count=0)

    async def _fetch_dataverse_items(self, dataverse_id) -> list[ItemResult]:
        async with self.network.GET(
            f"api/dataverses/{dataverse_id}/contents"
        ) as response:
            response_content = await response.json_content()
            items = await asyncio.gather(
                *[
                    self._get_dataverse_or_dataset_item(item)
                    for item in response_content["data"]
                ]
            )
            return [item for item in items if item]

    async def _get_dataverse_or_dataset_item(self, item: dict):
        match item["type"]:
            case "dataset":
                return await self._fetch_dataset(dataset_id=item["id"])
            case "dataverse":
                return await self._fetch_dataverse(item["id"])
        raise ValueError(f"Invalid item type: {item['type']}")

    async def _fetch_file(self, dataverse_id) -> ItemResult:
        async with self.network.GET(
            "api/files/:persistentId", query={"persistentId": dataverse_id}
        ) as response:
            return self._parse_datafile(await response.json_content())

    async def _fetch_dataverse(self, dataverse_id) -> ItemResult:
        async with self.network.GET(f"api/dataverses/{dataverse_id}") as response:
            return parse_dataverse(await response.json_content())

    async def _fetch_dataset_with_parser(
        self,
        dataset_id: str = None,
        persistent_id: str = None,
        parser=None,
    ) -> ItemResult | list[ItemResult] | None:
        url = f"api/datasets/{':persistentId' if persistent_id else dataset_id}/versions/:latest-published"
        query = {"persistentId": persistent_id} if persistent_id else {}
        async with self.network.GET(url, query=query) as response:
            if response.http_status == HTTPStatus.NOT_FOUND:
                return None
            return parser(await response.json_content())

    async def _fetch_dataset(
        self, dataset_id: str = None, persistent_id: str = None
    ) -> ItemResult:
        return await self._fetch_dataset_with_parser(
            dataset_id, persistent_id, parser=self._parse_dataset
        )

    async def _fetch_dataset_files(
        self, dataset_id: str = None, persistent_id: str = None
    ) -> list[ItemResult]:
        return await self._fetch_dataset_with_parser(
            dataset_id, persistent_id, parser=self._parse_dataset_files
        )

    def _parse_datafile(self, data: dict):
        if data.get("data"):
            data = data["data"]

        doi = data["dataFile"]["persistentId"]
        return ItemResult(
            item_id=f"file/{doi}",
            item_name=data["label"],
            item_type=ItemType.RESOURCE,
            item_link=self._make_url("file", doi),
            doi=doi,
        )

    def _parse_dataset_files(self, data: dict) -> list[ItemResult]:
        if data.get("data"):
            data = data["data"]
        try:
            return [self._parse_datafile(file) for file in data["files"]]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid dataset response:{e=}")

    def _parse_dataset(self, data: dict) -> ItemResult:
        if data.get("data"):
            data = data["data"]
        try:
            doi = data["datasetPersistentId"]
            return ItemResult(
                item_id=f"dataset/{doi}",
                item_name=[
                    item
                    for item in data["metadataBlocks"]["citation"]["fields"]
                    if item["typeName"] == "title"
                ][0]["value"],
                item_type=ItemType.FOLDER,
                item_link=self._make_url("dataset", doi),
                doi=doi,
            )
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid dataset response: {e=}")


###
# module-local helpers


def parse_dataverse_as_subitem(data: dict):
    return ItemResult(
        item_type=ItemType.FOLDER,
        item_name=data["title"],
        item_id=f'dataverse/{data["id"]}',
    )


def parse_dataverse(data: dict):
    if data.get("data"):
        data = data["data"]
    return ItemResult(
        item_type=ItemType.FOLDER,
        item_name=data["name"],
        item_id=f'dataverse/{data["alias"]}',
    )


def parse_mydata(data: dict):
    if data.get("data"):
        data = data["data"]
    return ItemSampleResult(
        items=[
            ItemResult(
                item_id=f"dataverse/{item['identifier']}",
                item_name=item["name"],
                item_type=ItemType.FOLDER,
            )
            for item in data["items"]
        ],
        total_count=data["total_count"],
        next_sample_cursor=(
            data["pagination"]["nextPageNumber"]
            if data["pagination"]["hasNextPageNumber"]
            else None
        ),
    )
