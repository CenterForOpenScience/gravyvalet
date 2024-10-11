from __future__ import annotations

from dataclasses import dataclass

from addon_imps.storage.utils import ItemResultable
from addon_toolkit.async_utils import join
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


FILE_CONTAINING_ARTICLES = (3, 4)


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
        if self._is_article_id(item_id):
            result = await self._fetch_article(item_id)
        elif self._is_project_id(item_id):
            result = await self._fetch_project(item_id)
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
        if item_type != ItemType.FOLDER and self._is_article_id(item_id):
            result = await self._fetch_article_files(item_id, cursor)
        elif item_type != ItemType.FILE and self._is_project_id(item_id):
            result = await self._fetch_project_articles(item_id, cursor)
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
        self, project_id: int | str, page_cursor: int
    ) -> list[Article]:
        async with self.network.GET(
            f"account/{project_id}/articles",
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
            f"account/{article_id}/files",
            query={
                "page": page_cursor,
                "page_size": 20,
            },
        ) as response:
            json = await response.json_content()
            return [File.from_json(project) for project in json]

    async def _fetch_projects(self, page: int) -> list[ItemResultable]:
        async with self.network.GET(
            "account/projects",
            query={
                "page": page,
                "page_size": 20,
            },
        ) as response:
            json = await response.json_content()
            return [Project.from_json(json_project) for json_project in json]

    async def _fetch_article(self, article_id: int | str) -> Article:
        assert self._is_article_id(article_id)

        async with self.network.GET(
            f"account/{article_id}",
        ) as response:
            return Article.from_json(await response.json_content())

    def _is_article_id(self, article_id: str) -> bool:
        return (
            "articles" in article_id
            and (article_id.startswith("projects/") and article_id.count("/") == 3)
            or (article_id.startswith("articles/") and article_id.count("/") == 1)
        )

    @staticmethod
    def _is_project_id(project_id: str) -> bool:
        return project_id.startswith("projects/") and project_id.count("/") == 1

    async def _fetch_project(self, project_id: str) -> Project:
        assert project_id.startswith("projects/")

        async with self.network.GET(
            f"account/{project_id}",
        ) as response:
            return Project.from_json(await response.json_content())


###
# module-local helpers


@dataclass(frozen=True, slots=True)
class File(ItemResultable):
    id: int
    name: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"file/{self.id}",
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
    id: int | None
    project_id: int | None
    title: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"{self.project_id or ''}articles/{self.id}",
            item_name=self.title,
            item_type=ItemType.FOLDER,
        )

    @classmethod
    def from_json(cls, json: dict, project_id: int = None):
        json["project_id"] = json.get("project_id", project_id)
        return super().from_json(json)
