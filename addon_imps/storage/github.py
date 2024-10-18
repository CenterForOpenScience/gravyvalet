from addon_service.common.exceptions import (
    ItemNotFound,
    UnexpectedAddonError,
)
from addon_toolkit.cursor import OffsetCursor
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import ItemType


class GitHubStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on GitHub

    see https://docs.github.com/en/rest
    """

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        async with self.network.GET("user") as response:
            json = await response.json_content()
            return str(json["id"])

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        async with self.network.GET(
            "user/repos",
        ) as response:
            if response.http_status == 200:
                json = await response.json_content()
                items = [self._parse_github_repo(repo) for repo in json]
                return storage.ItemSampleResult(
                    items=items, total_count=len(items)
                ).with_cursor(self._create_offset_cursor(len(items), page_cursor))

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if item_id == "." or not item_id:
            return storage.ItemResult(
                item_id="",
                item_name="GitHub",
                item_type=ItemType.FOLDER,
            )
        owner, repo, path = self._parse_github_item_id(item_id)
        if path == "":
            url = f"repos/{owner}/{repo}"
        else:
            url = f"repos/{owner}/{repo}/contents/{path}"
        async with self.network.GET(url) as response:
            if response.http_status == 200:
                json = await response.json_content()
                if path != "":
                    return self._parse_github_item(json, full_name=item_id)
                else:
                    return self._parse_github_repo(json)
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
        owner, repo, path = self._parse_github_item_id(item_id)
        query_params = self._params_from_cursor(page_cursor)
        async with self.network.GET(
            f"repos/{owner}/{repo}/contents/{path}",
            query=query_params,
        ) as response:
            if response.http_status == 200:
                json = await response.json_content()
                items = [
                    self._parse_github_item(entry, full_name=item_id) for entry in json
                ]
                return storage.ItemSampleResult(
                    items=items, total_count=len(items)
                ).with_cursor(self._create_offset_cursor(len(items), page_cursor))
            elif response.http_status == 404:
                raise ItemNotFound
            else:
                raise UnexpectedAddonError

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        if cursor:
            offset_cursor = OffsetCursor.from_str(cursor)
            return {
                "page": str(offset_cursor.offset),
                "per_page": str(offset_cursor.limit),
            }
        return {}

    def _parse_github_item_id(self, item_id: str) -> tuple[str, str, str]:
        try:
            owner_repo, path = item_id.split(":", maxsplit=1)
            owner, repo = owner_repo.split("/", maxsplit=1)
            return owner, repo, path
        except ValueError:
            raise ValueError(
                f"Invalid item_id format: {item_id}. Expected 'owner/repo:path'"
            )

    def _create_offset_cursor(
        self, total_items: int, current_cursor: str
    ) -> OffsetCursor:
        if not current_cursor:
            return OffsetCursor(offset=0, limit=total_items, total_count=total_items)
        cursor = OffsetCursor.from_str(current_cursor)
        return OffsetCursor(
            offset=cursor.offset + total_items,
            limit=cursor.limit,
            total_count=total_items,
        )

    def _parse_github_item(self, item_json: dict, full_name: str) -> storage.ItemResult:
        item_type = (
            ItemType.FILE if item_json.get("type") == "file" else ItemType.FOLDER
        )
        item_name = item_json["name"]
        if item_json.get("type") == "dir":
            item_id = full_name + item_name
        else:
            item_id = item_json["path"]
        return storage.ItemResult(
            item_id=item_id,
            item_name=item_json["name"],
            item_type=item_type,
        )

    def _parse_github_repo(self, repo_json: dict) -> storage.ItemResult:
        return storage.ItemResult(
            item_id=repo_json["full_name"] + ":",
            item_name=repo_json["name"],
            item_type=ItemType.FOLDER,
        )
