import dataclasses
import typing

from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import ItemType


class DropboxStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on dropbox.com
    see https://www.dropbox.com/developers/documentation/http/documentation
    """

    async def get_external_account_id(self, _: dict[str, str]) -> str:
        return ""

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        return await self.list_child_items(item_id="", page_cursor=page_cursor)

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if not item_id:
            return storage.ItemResult(
                item_id="",
                item_name="root folder",
                item_type=ItemType.FOLDER,
            )
        else:
            async with self.network.POST(
                "files/get_metadata",
                json={
                    "path": item_id,
                },
            ) as _response:
                _parsed = _DropboxParsedJson(await _response.json_content())
                return _parsed.single_item_result()

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        if page_cursor:
            async with self.network.POST(
                "files/list_folder/continue",
                json={"cursor": page_cursor},
            ) as _response:
                _parsed = _DropboxParsedJson(await _response.json_content())
                return storage.ItemSampleResult(
                    items=list(_parsed.item_results(item_type=item_type)),
                    total_count=len(_parsed.response_json["entries"]),
                    next_sample_cursor=_parsed.response_json["cursor"],
                )
        async with self.network.POST(
            "files/list_folder",
            json={"path": item_id, "recursive": False},
        ) as _response:
            _parsed = _DropboxParsedJson(await _response.json_content())
            items = list(_parsed.item_results(item_type=item_type))
            return storage.ItemSampleResult(
                items=items,
                total_count=len(items),
                next_sample_cursor=_parsed.response_json["cursor"],
            )


@dataclasses.dataclass
class _DropboxParsedJson:
    response_json: dict[str, typing.Any]

    ITEM_TYPE = {
        "folder": storage.ItemType.FOLDER,
        "file": storage.ItemType.FILE,
    }

    def single_item_result(self) -> storage.ItemResult:
        return self._parse_item(self.response_json)

    def _parse_item(self, item_json: dict[str, typing.Any]) -> storage.ItemResult:
        _item_type = self.ITEM_TYPE[item_json[".tag"]]
        _item_result = storage.ItemResult(
            item_id=item_json["id"],
            item_name=item_json["name"],
            item_type=_item_type,
        )
        return _item_result

    def _item_has_type(
        self,
        item_json: dict[str, typing.Any],
        item_type: storage.ItemType,
    ) -> bool:
        return self.ITEM_TYPE[item_json[".tag"]] == item_type

    def item_results(
        self,
        item_type: storage.ItemType | None = None,
    ) -> typing.Iterator[storage.ItemResult]:
        for _item in self.response_json["entries"]:
            if (item_type is None) or self._item_has_type(_item, item_type):
                yield self._parse_item(_item)
