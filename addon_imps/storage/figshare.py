from __future__ import annotations

import re
from dataclasses import dataclass

from addon_imps.storage.utils import ItemResultable
from addon_toolkit.async_utils import join
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


FILE_REGEX = re.compile(r"^articles/(?P<article_id>\d*)/files/(?P<file_id>\d*)$")
ARTICLE_REGEX = re.compile(r"^articles/(?P<article_id>\d*)$")
PROJECT_REGEX = re.compile(r"^projects/(?P<project_id>\d*)$")


class FigshareStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on figshare

    see https://developers.google.com/drive/api/reference/rest/v3/
    """

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        return ""

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        page_cursor = int(page_cursor or 1)
        items = await join(
            self._fetch_projects(page_cursor),
            self._fetch_articles(page_cursor),
        )
        return ItemSampleResult(
            items=[entry.item_result for entry in items],
            next_sample_cursor=str(page_cursor + 1),
        )

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if not item_id:
            return ItemResult(item_id="", item_name="", item_type=ItemType.FOLDER)
        if match := ARTICLE_REGEX.match(item_id):
            result = await self._fetch_article(match["article_id"])
        elif match := PROJECT_REGEX.match(item_id):
            result = await self._fetch_project(match["project_id"])
        elif match := FILE_REGEX.match(item_id):
            result = await self._fetch_file(match["article_id"], match["file_id"])
        else:
            raise ValueError("Malformed item_id")
        return result.item_result

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        cursor = int(page_cursor or 1)
        if item_type != ItemType.FOLDER and (match := ARTICLE_REGEX.match(item_id)):
            result = await self._fetch_article_files(match["article_id"], cursor)
        elif item_type != ItemType.FILE and (match := PROJECT_REGEX.match(item_id)):
            result = await self._fetch_project_articles(match["project_id"], cursor)
        else:
            result = []
        return ItemSampleResult(
            items=[item.item_result for item in result],
            next_sample_cursor=str(cursor + 1),
        )

    async def _fetch_articles(self, page_cursor: int) -> list[ItemResultable]:
        async with self.network.GET(
            "account/articles",
            query={
                "page": page_cursor,
                "page_size": 20,
            },
        ) as response:
            return [
                Article.from_json(project) for project in await response.json_content()
            ]

    async def _fetch_project_articles(
        self, project_id: str, page_cursor: int
    ) -> list[Article]:
        async with self.network.GET(
            f"account/projects/{project_id}/articles",
            query={
                "page": page_cursor,
                "page_size": 20,
            },
        ) as response:
            json = await response.json_content()
            return [Article.from_json(project) for project in json]

    async def _fetch_article_files(
        self, article_id: str, page_cursor: int
    ) -> list[File]:
        async with self.network.GET(
            f"account/articles/{article_id}/files",
            query={
                "page": page_cursor,
                "page_size": 20,
            },
        ) as response:
            return [
                File.from_json(file_json | {"article_id": article_id})
                for file_json in await response.json_content()
            ]

    async def _fetch_projects(self, page: int) -> list[ItemResultable]:
        async with self.network.GET(
            "account/projects",
            query={
                "page": page,
                "page_size": 20,
            },
        ) as response:
            return [
                Project.from_json(json_item)
                for json_item in await response.json_content()
            ]

    async def _fetch_article(self, article_id: str) -> Article:
        async with self.network.GET(f"account/articles/{article_id}") as response:
            return Article.from_json(await response.json_content())

    async def _fetch_project(self, project_id: str) -> Project:
        async with self.network.GET(f"account/projects/{project_id}") as response:
            return Project.from_json(await response.json_content())

    async def _fetch_file(self, article_id: str, file_id: str) -> File:
        async with self.network.GET(
            f"account/articles/{article_id}/files/{file_id}"
        ) as response:
            return File.from_json(
                await response.json_content() | {"article_id": article_id}
            )


###
# module-local helpers


@dataclass(frozen=True, slots=True)
class File(ItemResultable):
    id: int
    article_id: int
    name: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"articles{self.article_id}/files/{self.id}",
            item_name=self.name,
            item_type=ItemType.FILE,
        )


@dataclass(frozen=True, slots=True)
class Project(ItemResultable):
    id: int
    title: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"projects/{self.id}",
            item_name=self.title,
            item_type=ItemType.FOLDER,
        )


@dataclass(frozen=True, slots=True)
class Article(ItemResultable):
    id: int
    title: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"articles/{self.id}",
            item_name=self.title,
            item_type=ItemType.FOLDER,
        )

    @classmethod
    def from_json(cls, json: dict):
        return super(Article, cls).from_json(json)
