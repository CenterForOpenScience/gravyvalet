import dataclasses
import functools
import typing

from addon_toolkit.cursor import OffsetCursor
from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import ItemType


class BoxDotComStorageImp(storage.StorageAddonHttpRequestorImp):
    """storage on box.com

    see https://developer.box.com/reference/
    """

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        async with self.network.GET("users/me") as _response:
            _json = await _response.json_content()
            return str(_json["id"])

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        return storage.ItemSampleResult(
            items=[await self.get_item_info(_box_root_id())],
            total_count=1,
        )

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        async with self.network.GET(
            _box_item_url(item_id),
            query={"fields": "id,type,name,path"},
        ) as _response:
            return _BoxDotComParsedJson(
                await _response.json_content()
            ).single_item_result()

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        async with self.network.GET(
            _box_child_items_url(item_id),
            query={
                "fields": "id,type,name",
                **self._params_from_cursor(page_cursor),
            },
        ) as _response:
            _parsed = _BoxDotComParsedJson(await _response.json_content())
            return storage.ItemSampleResult(
                items=list(_parsed.item_results(item_type=item_type)),
            ).with_cursor(_parsed.cursor())

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        # https://developer.box.com/guides/api-calls/pagination/offset-based/
        try:
            _cursor = OffsetCursor.from_str(cursor)
            return {"offset": _cursor.offset, "limit": _cursor.limit}
        except ValueError:
            return {}


###
# module-local helpers


def _make_item_id(item_type: storage.ItemType, item_id: str) -> str:
    return ":".join((str(item_type.value), item_id))


def _parse_item_id(item_id: str) -> tuple[storage.ItemType, str]:
    try:
        if not item_id:
            return ItemType.FOLDER, "0"  # return root if empty
        (_type, _box_item_id) = item_id.split(":", maxsplit=1)
        return (storage.ItemType(_type), _box_item_id)
    except ValueError:
        raise ValueError(
            f'expected id of format "typeint:id", e.g. "1:1235" (got "{item_id}")'
        )


@functools.cache
def _box_root_id() -> str:
    return _make_item_id(storage.ItemType.FOLDER, "0")


def _box_file_url(file_id: str) -> str:
    return f"files/{file_id}"


def _box_folder_url(folder_id: str) -> str:
    return f"folders/{folder_id}"


def _box_item_url(item_id: str) -> str:
    _itemtype, _item_id = _parse_item_id(item_id)
    match _itemtype:
        case storage.ItemType.FILE:
            return _box_file_url(_item_id)
        case storage.ItemType.FOLDER:
            return _box_folder_url(_item_id)
        case _:
            raise NotImplementedError(f"no item url for type {_itemtype}")


def _box_child_items_url(item_id: str) -> str:
    return f"{_box_item_url(item_id)}/items"


@dataclasses.dataclass
class _BoxDotComParsedJson:
    response_json: dict[str, typing.Any]

    ITEM_TYPE: typing.ClassVar[dict[str, storage.ItemType]] = {
        "file": storage.ItemType.FILE,
        "folder": storage.ItemType.FOLDER,
        # "collection":
    }

    def single_item_result(self) -> storage.ItemResult:
        return self._parse_item(self.response_json)

    def item_results(
        self,
        item_type: storage.ItemType | None = None,
    ) -> typing.Iterator[storage.ItemResult]:
        # https://developer.box.com/reference/resources/items/
        for _item in self.response_json["entries"]:
            if (item_type is None) or self._item_has_type(_item, item_type):
                yield self._parse_item(_item)

    def cursor(self) -> OffsetCursor:
        return OffsetCursor(
            offset=self.response_json["offset"],
            limit=self.response_json["limit"],
            total_count=self.response_json["total_count"],
        )

    def _item_has_type(
        self,
        item_json: dict[str, typing.Any],
        item_type: storage.ItemType,
    ) -> bool:
        return self.ITEM_TYPE[item_json["type"]] == item_type

    def _parse_item(
        self,
        item_json: dict[str, typing.Any],
    ) -> storage.ItemResult:
        _item_type = self.ITEM_TYPE[item_json["type"]]
        _item_result = storage.ItemResult(
            item_id=_make_item_id(_item_type, item_json["id"]),
            item_name=item_json["name"],
            item_type=_item_type,
        )
        try:
            _path = item_json["path_collection"]
        except KeyError:
            pass
        else:
            _item_result.item_path = self._parse_path_collection(_path)
        return _item_result

    def _parse_path_collection(
        self, path_json: dict[str, typing.Any]
    ) -> list[storage.ItemResult]:
        return [
            self._parse_item(_path_item) for _path_item in path_json.get("entries", ())
        ]
