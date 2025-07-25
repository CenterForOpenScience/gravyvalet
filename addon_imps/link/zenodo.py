from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus

from django.core.exceptions import ValidationError

from addon_toolkit.interfaces.link import (
    ItemResult,
    ItemSampleResult,
    ItemType,
    LinkAddonHttpRequestorImp,
    SupportedResourceTypes,
)


DEPOSITION_REGEX = re.compile(r"^deposition/(?P<id>\d+)$")
FILE_REGEX = re.compile(r"^file/(?P<deposition_id>\d+)/(?P<file_id>\d+)$")


class _ResourceTypeMapping(Enum):
    PUBLICATION = SupportedResourceTypes.Text
    POSTER = SupportedResourceTypes.Text
    PRESENTATION = SupportedResourceTypes.Text
    DATASET = SupportedResourceTypes.Dataset
    IMAGE = SupportedResourceTypes.Image
    VIDEO = SupportedResourceTypes.Audiovisual
    SOFTWARE = SupportedResourceTypes.Software
    LESSON = SupportedResourceTypes.Text
    PHYSICALOBJECT = SupportedResourceTypes.PhysicalObject
    OTHER = SupportedResourceTypes.Other


@dataclass
class ZenodoLinkImp(LinkAddonHttpRequestorImp):
    """Storage on Zenodo

    See https://developers.zenodo.org/ for API documentation
    """

    async def build_url_for_id(self, item_id: str) -> str:
        """
        This method is used by ConfiguredLinkAddon to construct user-facing url,
        which will take them to the configured resource web page
        """
        if match := DEPOSITION_REGEX.match(item_id):
            return self._build_deposition_url(match["id"])
        elif match := FILE_REGEX.match(item_id):
            return self._build_file_url(match["deposition_id"], match["file_id"])
        else:
            raise ValidationError(f"Invalid {item_id=}")

    def _build_file_url(self, deposition_id: str, file_id: str):
        return f"{self.config.external_web_url}/record/{deposition_id}/files/{file_id}"

    def _build_deposition_url(self, deposition_id: str):
        return f"{self.config.external_web_url}/deposition/{deposition_id}"

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        """
        This method fetches external account's id on the provider side, and is meant for use internally.

        For Zenodo it has to fetch user's depositions and take owner id form it,
        as Zenodo API does not provide direct way to fetch user's internal id
        """
        async with self.network.GET("api/deposit/depositions") as response:
            if not response.http_status.is_success:
                raise ValidationError(
                    "Could not get Zenodo account id, check your API Token"
                )
            content = await response.json_content()
            if content and len(content) > 0:
                return str(content[0].get("owner", ""))
            return "zenodo_user"  # Fallback if no depositions found

    async def list_root_items(self, page_cursor: str = "") -> ItemSampleResult:
        """
        This method lists root (top level ) from external provider.
        Please note that it must return only public items.

        For Zenodo it fetches user's depositions and filters them to be public on client's side
        (as the API does not such filtering)
        """
        page = 1
        if page_cursor:
            try:
                page = int(page_cursor)
            except ValueError:
                pass

        async with self.network.GET(
            "api/deposit/depositions",
            query=[("page", page), ("size", 10)],
        ) as response:
            content = await response.json_content()
            return self._parse_depositions_list(content, page)

    def _parse_depositions_list(
        self, raw_content: list[dict], current_page: int
    ) -> ItemSampleResult:
        """Parse the response from the depositions endpoint.

        The depositions endpoint returns a list of depositions directly, not wrapped in a hits object.
        Also filter only public (only published) depositions.
        """
        items = []
        for deposition in raw_content:
            parsed = self._parse_deposition(deposition)
            if parsed.doi:
                items.append(parsed)

        next_page = current_page + 1 if len(raw_content) == 10 else None
        prev_page = current_page - 1 if current_page > 1 else None

        return ItemSampleResult(
            items=items,
            total_count=len(items),
            this_sample_cursor=str(current_page),
            next_sample_cursor=str(next_page) if next_page else None,
            prev_sample_cursor=str(prev_page) if prev_page else None,
            first_sample_cursor="1",
        )

    async def get_item_info(self, item_id: str) -> ItemResult:
        """
        This method fetches desired item from an API
        """
        if not item_id:
            return ItemResult(item_id="", item_name="", item_type=ItemType.FOLDER)
        elif match := DEPOSITION_REGEX.match(item_id):
            return await self._fetch_deposition(match["id"])
        elif match := FILE_REGEX.match(item_id):
            return await self._fetch_file(match["record_id"], match["file_id"])
        else:
            raise ValueError(f"Invalid item id: {item_id}")

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: ItemType | None = None,
    ) -> ItemSampleResult:
        """
        This method lists children items of requested id. Used to navigate item tree (if there is one).

        For Zenodo it fetches files for given depositions, as there is no apparent item tree
        """
        if not item_id:
            return await self.list_root_items(page_cursor)
        elif match := DEPOSITION_REGEX.match(item_id):
            files = await self._fetch_record_files(match["id"])
            return ItemSampleResult(
                items=files,
                total_count=len(files),
            )
        else:
            return ItemSampleResult(items=[], total_count=0)

    async def _fetch_record_files(self, record_id: str) -> list[ItemResult]:
        """
        Helper used to fetch deposition's files
        """
        async with self.network.GET(
            f"api/deposit/depositions/{record_id}/files"
        ) as response:
            if response.http_status == HTTPStatus.NOT_FOUND:
                return []
            files = await response.json_content()
            return [self._parse_file(file, record_id) for file in files]

    async def _fetch_file(self, record_id: str, file_id: str) -> ItemResult:
        """
        Helper used to fetch deposition's file
        """
        async with self.network.GET(
            f"api/deposit/depositions/{record_id}/files/{file_id}"
        ) as response:
            if response.http_status == HTTPStatus.NOT_FOUND:
                raise ValueError(f"Record not found: {record_id}")

            file = await response.json_content()

            return self._parse_file(file, record_id)

    def _parse_file(self, file: dict, record_id: str) -> ItemResult:
        """
        Helper which parses file response into ItemResult
        """
        return ItemResult(
            item_id=f"file/{record_id}/{file.get('id')}",
            item_name=file.get("filename"),
            item_type=ItemType.RESOURCE,
            item_link=f"{self.config.external_web_url}/record/{record_id}/files/{file.get('filename')}",
        )

    async def _fetch_deposition(self, deposition_id: str) -> ItemResult:
        """
        Helper used to fetch deposition
        """
        async with self.network.GET(
            f"api/deposit/depositions/{deposition_id}"
        ) as response:
            if response.http_status == HTTPStatus.NOT_FOUND:
                raise ValueError(f"Record not found: {deposition_id}")
            content = await response.json_content()
            return self._parse_deposition(content)

    def _parse_deposition(self, raw: dict) -> ItemResult:
        """
        Helper which parses deposition response into ItemResult
        """
        deposition_id = raw.get("id")

        metadata = raw.get("metadata", {})

        resource_type = self._map_resource_type(
            metadata.get("resource_type", {}).get("type", "")
        )

        return ItemResult(
            item_id=f"deposition/{deposition_id}",
            item_name=metadata.get("title", f"Deposition {deposition_id}"),
            item_type=ItemType.FOLDER,
            resource_type=resource_type,
            item_link=f"{self.config.external_web_url}/record/{deposition_id}",
            doi=metadata.get("doi", ""),
        )

    def _map_resource_type(self, zenodo_type: str) -> SupportedResourceTypes | None:
        """Map Zenodo resource types to SupportedResourceTypes"""
        if zenodo_type:
            return _ResourceTypeMapping[zenodo_type.upper()]
        return None
