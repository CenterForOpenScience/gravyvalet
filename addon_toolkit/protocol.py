import dataclasses
import enum
import inspect
import logging
from typing import (
    Iterable,
    Iterator,
)

from .declarator import ClassDeclarator
from .operation import (
    AddonOperationDeclaration,
    addon_operation,
)


__all__ = (
    "addon_protocol",
    "AddonProtocolDeclaration",
)

_logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class AddonProtocolDeclaration:
    """dataclass for the operations declared on a class decorated with `addon_protocol`"""

    protocol_cls: type

    def get_operations(
        self, *, capabilities: Iterable[enum.Enum] = ()
    ) -> Iterator[AddonOperationDeclaration]:
        _capability_set = set(capabilities)
        for _name, _fn in inspect.getmembers(self.protocol_cls, inspect.isfunction):
            try:
                _op = addon_operation.get_declaration(_fn)
            except ValueError:
                continue  # not an operation
            if (not _capability_set) or (_op.capability in _capability_set):
                yield _op

    def get_operation_by_name(self, op_name: str) -> AddonOperationDeclaration:
        return addon_operation.get_declaration(
            getattr(self.protocol_cls, op_name),
        )


# the class decorator itself
addon_protocol = ClassDeclarator(
    declaration_dataclass=AddonProtocolDeclaration,
    field_for_target="protocol_cls",
)
