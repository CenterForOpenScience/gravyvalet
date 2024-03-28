import typing

from addon_toolkit import storage


ROOT_FOLDER_ID: str = "0"


class BoxDotComStorageImp(storage.StorageAddon):
    """storage on box.com

    see https://developer.box.com/reference/
    """

    async def get_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        async with self.network.GET(
            _box_root_folder_items_url(),
            query=self._list_params(page_cursor),
        ) as _response:
            _json_content = await _response.json_content()
            return storage.ItemSampleResult(
                items=list(self._parse_box_items(_json_content))
                # TODO: cursors
            )

    def _list_params(self, cursor: str = "") -> dict[str, str]:
        # https://developer.box.com/guides/api-calls/pagination/marker-based/
        _query_params = {"usemarker": "true"}
        if cursor:
            _query_params["marker"] = cursor
        return _query_params

    def _parse_box_items(
        self, items_json: typing.Any
    ) -> typing.Iterator[storage.ItemResult]:
        # https://developer.box.com/reference/resources/items/
        for _item in items_json["entries"]:
            yield self._parse_box_item(_item)

    def _parse_box_item(
        self,
        item_json: dict[str, typing.Any],
    ) -> storage.ItemResult:
        return storage.ItemResult(
            item_json["id"],
            item_json["name"],
        )


###
# module-local helpers


def _box_root_folder_items_url() -> str:
    return _box_folder_items_url(ROOT_FOLDER_ID)


def _box_folder_url(folder_id: str) -> str:
    return f"folders/{folder_id}"


def _box_folder_items_url(folder_id: str) -> str:
    return f"{_box_folder_url(folder_id)}/items"
