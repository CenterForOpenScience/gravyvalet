import dataclasses
import typing

from addon_toolkit import storage
from addon_toolkit.cursor import OffsetCursor


ROOT_FOLDER_ID: str = "0"


class BoxDotComStorageImp(storage.StorageAddonImp):
    """storage on box.com

    see https://developer.box.com/reference/
    """

    waterbutler_provider_key = "box"

    async def get_root_folders(self, page_cursor: str = "") -> storage.ItemSampleResult:
        return await self.get_child_folders(
            item_id=ROOT_FOLDER_ID,
            page_cursor=page_cursor,
        )

    async def get_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        return await self.get_child_items(
            item_id=ROOT_FOLDER_ID,
            page_cursor=page_cursor,
        )

    async def get_child_folders(
        self,
        item_id: str,
        page_cursor: str = "",
    ) -> storage.ItemSampleResult:
        return await self.get_child_items(
            item_id=ROOT_FOLDER_ID,
            page_cursor=page_cursor,
            item_type=storage.ItemType.FOLDER,
        )

    async def get_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        async with self.network.GET(
            _box_folder_items_url(item_id),
            query={
                "fields": "id,type,name",
                **self._params_from_cursor(page_cursor),
            },
        ) as _response:
            _parsed = _BoxDotComParsedJson(await _response.json_content())
            return storage.ItemSampleResult(
                items=list(_parsed.item_results(item_type=item_type)),
                cursor=_parsed.cursor(),
            )

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        # https://developer.box.com/guides/api-calls/pagination/offset-based/
        try:
            _cursor = OffsetCursor.from_str(cursor)
            return {"offset": _cursor.offset, "limit": _cursor.limit}
        except ValueError:
            return {}


###
# module-local helpers


def _box_folder_url(folder_id: str) -> str:
    return f"folders/{folder_id}"


def _box_folder_items_url(folder_id: str) -> str:
    return f"{_box_folder_url(folder_id)}/items"


@dataclasses.dataclass
class _BoxDotComParsedJson:
    response_json: dict[str, typing.Any]

    ITEM_TYPE: typing.ClassVar[dict[str, storage.ItemType]] = {
        "file": storage.ItemType.FILE,
        "folder": storage.ItemType.FOLDER,
    }

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
        return storage.ItemResult(
            item_id=item_json["id"],
            item_name=item_json["name"],
            item_type=self.ITEM_TYPE[item_json["type"]],
        )
