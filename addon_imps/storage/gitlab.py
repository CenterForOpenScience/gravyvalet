from __future__ import annotations

import urllib
from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import (
    quote_plus,
    unquote_plus,
    urlparse,
)

from addon_imps.storage.utils import ItemResultable
from addon_service.common.exceptions import ItemNotFound
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


FOLDER_ITEM_TYPES = frozenset(["subfolder", "tree", "folder"])


class GitlabStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on gitlab

    see https://developers.google.com/drive/api/reference/rest/v3/
    """

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        async with self.network.GET("user/preferences") as response:
            resp_json = await response.json_content()
            return resp_json.get("user_id", "")

    async def build_wb_config(self, root_folder_id: str, host: str) -> dict:
        item_id = ItemId.parse(root_folder_id)
        owner, repo_name = unquote_plus(item_id.repo_id).split("/")
        repo = await self._get_repository(item_id.repo_id)
        url = urlparse(host)
        return {
            "repo": repo_name,
            "repo_id": str(repo.id),
            "owner": owner,
            "host": f"{url.scheme}://{url.hostname}",
        }

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        query_params = self._page_cursor_or_query(
            page_cursor,
            {
                "membership": "true",
                "simple": "true",
                "pagination": "true",
                "sort": "asc",
            },
        )
        async with self.network.GET("projects", query=query_params) as response:
            resp = await response.json_content()
            return ItemSampleResult(
                items=[Repository.from_json(item).item_result for item in resp],
                next_sample_cursor=self._get_next_cursor(response.headers),
            )

    def _get_next_cursor(self, headers):
        if not headers.get("Link"):
            return
        next_link_candidates = [
            item for item in headers["Link"].split(",") if 'rel="next"' in item
        ]
        if not next_link_candidates:
            return None
        next_link_candidate: str = next_link_candidates[0]

        return (
            next_link_candidate.strip()
            .removeprefix("<")
            .removesuffix('>; rel="next"')
            .split("?", maxsplit=1)[1]
        )

    def _page_cursor_or_query(self, page_cursor: str, query: dict):
        if page_cursor:
            return dict(urllib.parse.parse_qsl(page_cursor))
        else:
            return query

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        parsed_id = ItemId.parse(item_id)
        if parsed_id.file_path:
            return await self.get_file_or_folder(parsed_id)

        return (await self._get_repository(parsed_id.repo_id)).item_result

    async def _get_repository(self, repo_id):
        async with self.network.GET(f"projects/{repo_id}") as response:
            content = await response.json_content()
            return Repository.from_json(content)

    async def get_file_or_folder(self, parsed_id: ItemId):
        async with self.network.GET(f"projects/{parsed_id.repo_id}") as response:
            content = await response.json_content()
            ref = content.get("default_branch")
        if file_item := await self._get_file(parsed_id, ref):
            return file_item
        # try to list files under folder, if it succeeds, proceed to return folder, else propagate the error
        await self.list_child_items(parsed_id.raw_id)
        return ItemResult(
            item_name=parsed_id.file_path.split("/")[-1],
            item_id=parsed_id.raw_id,
            item_type=ItemType.FOLDER,
        )

    async def _get_file(self, parsed_id, ref):
        async with self.network.GET(
            f"projects/{parsed_id.repo_id}/repository/files/{quote_plus(parsed_id.file_path)}",
            query={"ref": ref},
        ) as response:
            content = await response.json_content()
            if "file_name" not in content:
                return None
            return ItemResult(
                item_name=content["file_name"],
                item_id=parsed_id.raw_id,
                item_type=ItemType.FILE,
            )

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        parsed_id = ItemId.parse(item_id)
        query_params = self._page_cursor_or_query(
            page_cursor,
            {
                "pagination": "keyset",
                "path": parsed_id.file_path,
                "sort": "asc",
                "order_by": "name",
            },
        )
        async with self.network.GET(
            f"projects/{parsed_id.repo_id}/repository/tree",
            query=query_params,
        ) as response:
            if response.http_status == HTTPStatus.NOT_FOUND:
                raise ItemNotFound
            content = await response.json_content()
            res_items = [parse_item(parsed_id.repo_id, item) for item in content]

            if item_type:
                res_items = [item for item in res_items if item.item_type == item_type]
            return ItemSampleResult(
                items=res_items,
                next_sample_cursor=self._get_next_cursor(response.headers),
            )


@dataclass(frozen=True)
class ItemId:
    repo_id: str
    file_path: str
    raw_id: str

    @classmethod
    def parse(cls, item_id: str) -> ItemId:
        repo_id, file_path = item_id.split(":", maxsplit=1)
        return cls(
            repo_id=repo_id,
            file_path=file_path,
            raw_id=item_id,
        )


def parse_item(repo_id: str, raw_item: dict) -> ItemResult:
    return ItemResult(
        item_id=f'{repo_id}:{raw_item["path"]}',
        item_type=(
            ItemType.FOLDER if raw_item["type"] in FOLDER_ITEM_TYPES else ItemType.FILE
        ),
        item_name=raw_item["name"],
    )


###
# module-local helpers
@dataclass(frozen=True, slots=True)
class Repository(ItemResultable):
    path_with_namespace: str
    id: int
    name: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"{quote_plus(self.path_with_namespace)}:",
            item_name=self.name,
            item_type=ItemType.FOLDER,
        )
