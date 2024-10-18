from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import fields
from typing import Self

from addon_toolkit.interfaces.storage import ItemResult


class ItemResultable(ABC):
    @property
    @abstractmethod
    def item_result(self) -> ItemResult: ...

    @classmethod
    def from_json(cls, json: dict) -> Self:
        return cls(
            **{key.name: json[key.name] for key in fields(cls) if json.get(key.name)}
        )
