from __future__ import annotations

from dataclasses import dataclass

from addon_imps.storage.utils import ItemResultable
from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import (
    ItemResult,
    ItemSampleResult,
    ItemType,
)


class GitlabStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on gitlab

    see https://developers.google.com/drive/api/reference/rest/v3/
    """

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        async with self.network.GET("user/preferences") as response:
            resp_json = await response.json_content()
            return resp_json.get("user_id", "")

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        page_cursor = int(page_cursor or 1)
        async with self.network.GET(
            "projects", query={"membership": "true", "page": page_cursor}
        ) as response:
            resp = await response.json_content()
            return ItemSampleResult(
                items=[Repository.from_json(item).item_result for item in resp],
                next_sample_cursor=str(page_cursor + 1),
            )

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        item_id = item_id or "root"
        async with self.network.GET(f"drive/v3/files/{item_id}") as response:
            if response.http_status == 200:
                json = await response.json_content()
                return Repository.from_json(json).item_result
            elif response.http_status == 404:
                raise ItemNotFound
            else:
                raise UnexpectedAddonError

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        query = {"q": f"'{item_id}' in parents"}
        if page_cursor:
            query["pageToken"] = page_cursor
        if item_type == ItemType.FOLDER:
            query["q"] += " and mimeType='application/vnd.google-apps.folder'"
        elif item_type == ItemType.FILE:
            query["q"] += " and mimeType!='application/vnd.google-apps.folder'"

        async with self.network.GET("drive/v3/files", query=query) as response:
            return Repository.from_json(
                await response.json_content()
            ).item_sample_result


###
# module-local helpers
@dataclass(frozen=True, slots=True)
class Repository(ItemResultable):
    id: str
    name: str

    @property
    def item_result(self) -> ItemResult:
        return ItemResult(
            item_id=f"repository/{self.id}",
            item_name=self.name,
            item_type=ItemType.FOLDER,
        )
