import base64
import dataclasses
import json
import typing


class DataclassInstance(typing.Protocol):
    __dataclass_fields__: typing.ClassVar[dict[str, typing.Any]]


SomeDataclassInstance = typing.TypeVar("SomeDataclassInstance", bound=DataclassInstance)


def encode_cursor_dataclass(dataclass_instance: DataclassInstance) -> str:
    _as_json = json.dumps(dataclasses.astuple(dataclass_instance))
    _cursor_bytes = base64.b64encode(_as_json.encode())
    return _cursor_bytes.decode()


def decode_cursor_dataclass(
    cursor: str, dataclass_class: type[SomeDataclassInstance]
) -> SomeDataclassInstance:
    _as_list = json.loads(base64.b64decode(cursor))
    return dataclass_class(*_as_list)


class Cursor(DataclassInstance, typing.Protocol):
    @classmethod
    def from_str(cls, cursor: str) -> typing.Self:
        return decode_cursor_dataclass(cursor, cls)

    @property
    def this_cursor_str(self) -> str:
        return encode_cursor_dataclass(self)

    @property
    def next_cursor_str(self) -> str | None: ...

    @property
    def prev_cursor_str(self) -> str | None: ...

    @property
    def first_cursor_str(self) -> str: ...

    @property
    def is_first_page(self) -> bool: ...

    @property
    def is_last_page(self) -> bool: ...

    @property
    def has_many_more(self) -> bool: ...


@dataclasses.dataclass
class OffsetCursor(Cursor):
    offset: int
    limit: int
    total_count: int  # use -1 to mean "many more"

    MAX_INDEX: typing.ClassVar[int] = 9999

    @property
    def next_cursor_str(self) -> str | None:
        _next = dataclasses.replace(self, offset=(self.offset + self.limit))
        return encode_cursor_dataclass(_next) if _next.is_valid_cursor() else None

    @property
    def prev_cursor_str(self) -> str | None:
        _prev = dataclasses.replace(self, offset=(self.offset - self.limit))
        return encode_cursor_dataclass(_prev) if _prev.is_valid_cursor() else None

    @property
    def first_cursor_str(self) -> str:
        return encode_cursor_dataclass(dataclasses.replace(self, offset=0))

    @property
    def is_first_page(self) -> bool:
        return self.offset == 0

    @property
    def is_last_page(self) -> bool:
        return (self.offset + self.limit) >= self.total_count

    @property
    def has_many_more(self) -> bool:
        return self.total_count == -1

    def max_index(self) -> int:
        return (
            self.MAX_INDEX
            if self.has_many_more
            else min(self.total_count, self.MAX_INDEX)
        )

    def is_valid_cursor(self) -> bool:
        return (self.limit > 0) and (0 <= self.offset < self.max_index())
