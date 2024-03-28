import dataclasses
import typing

from addon_toolkit import storage
from addon_toolkit.cursor import OffsetCursor


ROOT_FOLDER_ID: str = "0"


@dataclasses.dataclass(frozen=True)
class BoxDotComStorageImp(storage.StorageAddon):
    """storage on box.com

    see https://developer.box.com/reference/
    """

    async def get_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        async with self.network.GET(
            _box_root_folder_items_url(),
            query=self._params_from_cursor(page_cursor),
        ) as _response:
            _parsed = _BoxDotComParsedJson(await _response.json_content())
            return storage.ItemSampleResult(
                items=list(_parsed.item_results()),
                cursor=_parsed.cursor(),
            )

    def _params_from_cursor(self, cursor: str = "") -> dict[str, str]:
        # https://developer.box.com/guides/api-calls/pagination/offset-based/
        try:
            _offset, _limit = cursor.split("|")
            return {"offset": _offset, "limit": _limit}
        except ValueError:
            return {}


###
# module-local helpers


def _box_root_folder_items_url() -> str:
    return _box_folder_items_url(ROOT_FOLDER_ID)


def _box_folder_url(folder_id: str) -> str:
    return f"folders/{folder_id}"


def _box_folder_items_url(folder_id: str) -> str:
    return f"{_box_folder_url(folder_id)}/items"


@dataclasses.dataclass
class _BoxDotComParsedJson:
    response_json: dict[str, typing.Any]

    def item_results(self) -> typing.Iterator[storage.ItemResult]:
        # https://developer.box.com/reference/resources/items/
        for _item in self.response_json["entries"]:
            yield self._parse_item(_item)

    def cursor(self) -> OffsetCursor:
        return OffsetCursor(
            offset=self.response_json["offset"],
            limit=self.response_json["limit"],
            total_count=self.response_json["total_count"],
        )

    def _parse_item(
        self,
        item_json: dict[str, typing.Any],
    ) -> storage.ItemResult:
        return storage.ItemResult(
            item_id=item_json["id"],
            item_name=item_json["name"],
        )
