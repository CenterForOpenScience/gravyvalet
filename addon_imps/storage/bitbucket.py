import dataclasses
from urllib.parse import (
    parse_qs,
    urlparse,
)

from addon_toolkit.cursor import Cursor
from addon_toolkit.interfaces import storage


class NextLinkCursor(Cursor):
    def __init__(self, next_link: str | None):
        self._next_link = next_link

    @property
    def this_cursor_str(self) -> str:
        return ""

    @property
    def next_cursor_str(self) -> str | None:
        return self._next_link

    @property
    def prev_cursor_str(self) -> str | None:
        return None

    @property
    def first_cursor_str(self) -> str:
        return ""


@dataclasses.dataclass
class BitbucketStorageImp(storage.StorageAddonHttpRequestorImp):
    workspace_slug: str = dataclasses.field(init=False, default="")

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        async with self.network.GET("user") as response:
            json_data = await response.json_content()
            uuid = json_data.get("uuid")
            if not uuid:
                raise ValueError("Failed to retrieve user UUID")

        async with self.network.GET("user/permissions/workspaces") as response:
            data = await response.json_content()
            workspaces = data.get("values", [])
            if not workspaces:
                raise ValueError("No workspaces found")

            for workspace in workspaces:
                slug = workspace["workspace"]["slug"]
                perm = workspace.get("permission")
                if perm in ["admin", "contributor", "member", "owner"]:
                    self.workspace_slug = slug
                    break
            else:
                raise ValueError("No suitable workspace found")
        return uuid

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        params = self._params_from_cursor(page_cursor)
        params["role"] = "member"
        params["pagelen"] = "100"
        endpoint = f"repositories/{self.workspace_slug}"
        try:
            async with self.network.GET(endpoint, query=params) as response:
                json_data = await response.json_content()
        except Exception as e:
            raise ValueError(f"Failed to fetch repositories: {e}")

        items = []
        for repo in json_data.get("values", []):
            full_name = repo.get("full_name")
            name = repo.get("name") or "Unnamed Repository"
            if not full_name:
                continue
            item_id = self._make_item_id(storage.ItemType.FOLDER, full_name)
            items.append(
                storage.ItemResult(
                    item_id=item_id,
                    item_name=name,
                    item_type=storage.ItemType.FOLDER,
                )
            )
        result = storage.ItemSampleResult(items=items)
        next_cursor = json_data.get("next")
        cursor = NextLinkCursor(next_link=next_cursor)
        result = result.with_cursor(cursor)
        return result

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if not item_id:
            raise ValueError("Item ID is empty.")
        item_type, actual_id = self._parse_item_id(item_id)
        if item_type == storage.ItemType.FOLDER:
            endpoint = f"repositories/{actual_id}"
            try:
                async with self.network.GET(endpoint) as response:
                    json_data = await response.json_content()
            except Exception as e:
                raise ValueError(f"Failed to fetch item info: {e}")
            name = json_data.get("name") or "Unnamed Repository"
            return storage.ItemResult(
                item_id=item_id,
                item_name=name,
                item_type=item_type,
            )
        else:
            repo_full_name, path_param = self._split_repo_full_name_and_path(actual_id)
            endpoint = f"repositories/{repo_full_name}/src/HEAD/{path_param}"
            try:
                async with self.network.GET(endpoint) as response:
                    json_data = await response.json_content()
            except Exception:
                raise ValueError(f"File not found: {item_id}")
            file_name = path_param.split("/")[-1] if path_param else "Unnamed File"
            return storage.ItemResult(
                item_id=item_id,
                item_name=file_name,
                item_type=storage.ItemType.FILE,
            )

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        if not item_id:
            raise ValueError("Item ID is empty.")
        item_type_id, actual_id = self._parse_item_id(item_id)
        if item_type_id != storage.ItemType.FOLDER:
            raise ValueError("Only folders can have child items")
        params = self._params_from_cursor(page_cursor)
        repo_full_name, path_param = self._split_repo_full_name_and_path(actual_id)
        endpoint = f"repositories/{repo_full_name}/src/HEAD/{path_param}"
        try:
            async with self.network.GET(endpoint, query=params) as response:
                json_data = await response.json_content()
        except Exception as e:
            raise ValueError(f"Failed to list child items: {e}")
        items = []
        for item in json_data.get("values", []):
            item_type_value = (
                storage.ItemType.FOLDER
                if item["type"] == "commit_directory"
                else storage.ItemType.FILE
            )
            if item_type is not None and item_type != item_type_value:
                continue
            path = item.get("path")
            if not path:
                continue
            item_name = path.split("/")[-1] or "Unnamed Item"
            item_id_value = self._make_item_id(
                item_type_value, f"{repo_full_name}/{path}"
            )
            items.append(
                storage.ItemResult(
                    item_id=item_id_value,
                    item_name=item_name,
                    item_type=item_type_value,
                )
            )
        result = storage.ItemSampleResult(items=items)
        next_cursor = json_data.get("next")
        cursor = NextLinkCursor(next_link=next_cursor)
        result = result.with_cursor(cursor)
        return result

    def _split_repo_full_name_and_path(self, actual_id: str) -> tuple[str, str]:
        parts = actual_id.split("/", 2)
        if len(parts) < 2:
            raise ValueError(
                "Invalid actual_id format. Expected 'workspace/repo_slug' or 'workspace/repo_slug/path/to/item'."
            )
        repo_full_name = f"{parts[0]}/{parts[1]}"
        path_param = parts[2] if len(parts) > 2 else ""
        return repo_full_name, path_param

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        if not cursor:
            return {}
        parsed_url = urlparse(cursor)
        query_params = parse_qs(parsed_url.query)
        flat_query_params = {k: v[0] for k, v in query_params.items()}
        return flat_query_params

    def _make_item_id(self, item_type: storage.ItemType, item_id: str) -> str:
        return f"{item_type.value}:{item_id}"

    def _parse_item_id(self, item_id: str) -> tuple[storage.ItemType, str]:
        if not item_id:
            raise ValueError("Item ID is empty.")
        try:
            _type_str, actual_id = item_id.split(":", 1)
            return storage.ItemType(_type_str), actual_id
        except ValueError:
            raise ValueError(f"Invalid item_id format: {item_id!r}")
