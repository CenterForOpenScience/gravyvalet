import typing


class AnyDataclassInstance(typing.Protocol):
    __dataclass_fields__: typing.ClassVar[dict[str, typing.Any]]


DataclassInstance = typing.TypeVar("DataclassInstance", bound=AnyDataclassInstance)
