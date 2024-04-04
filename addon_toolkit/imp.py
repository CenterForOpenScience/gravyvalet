import dataclasses
import enum
from typing import (
    Iterable,
    Iterator,
)

from .json_arguments import bound_kwargs_from_json
from .operation import AddonOperationDeclaration
from .protocol import (
    AddonProtocolDeclaration,
    addon_protocol,
)


__all__ = (
    "AddonImp",
    "AddonOperationImp",
)


@dataclasses.dataclass(frozen=True)
class AddonImp:
    """dataclass for an addon protocol and a class supposed to implement that protocol"""

    addon_protocol_cls: dataclasses.InitVar[type]
    imp_cls: type
    imp_number: int
    addon_protocol: AddonProtocolDeclaration = dataclasses.field(init=False)

    def __post_init__(self, addon_protocol_cls):
        super().__setattr__(  # using __setattr__ to bypass dataclass frozenness
            "addon_protocol",
            addon_protocol.get_declaration(addon_protocol_cls),
        )

    def get_operation_imps(
        self, *, capabilities: Iterable[enum.Enum] = ()
    ) -> Iterator["AddonOperationImp"]:
        for _operation in self.addon_protocol.get_operations(capabilities=capabilities):
            try:
                yield AddonOperationImp(addon_imp=self, operation=_operation)
            except NotImplementedError:  # TODO: helpful exception type
                pass  # operation not implemented

    def get_operation_imp_by_name(self, operation_name: str) -> "AddonOperationImp":
        try:
            return AddonOperationImp(
                addon_imp=self,
                operation=self.addon_protocol.get_operation_by_name(operation_name),
            )
        except NotImplementedError:  # TODO: helpful exception type
            raise ValueError(f'unknown operation name "{operation_name}"')


@dataclasses.dataclass(frozen=True)
class AddonOperationImp:
    """dataclass for an operation implemented as part of an addon protocol implementation"""

    addon_imp: AddonImp
    operation: AddonOperationDeclaration

    def __post_init__(self):
        _protocol_fn = getattr(
            self.addon_imp.addon_protocol.protocol_cls, self.operation.name
        )
        if self.imp_function is _protocol_fn:
            raise NotImplementedError(  # TODO: helpful exception type
                f"operation '{self.operation}' not implemented by {self.addon_imp}"
            )

    @property
    def imp_function(self):
        return getattr(self.addon_imp.imp_cls, self.operation.name)

    def call_with_json_kwargs(self, addon_instance: object, json_kwargs: dict):
        assert isinstance(addon_instance, self.addon_imp.imp_cls)
        _bound_kwargs = bound_kwargs_from_json(
            self.operation.call_signature, json_kwargs
        )
        _method = getattr(addon_instance, self.operation.name)
        _result = _method(
            *_bound_kwargs.args, **_bound_kwargs.kwargs
        )  # TODO: if async, use async_to_sync
        assert isinstance(_result, self.operation.return_dataclass)
        return _result

    # TODO: async def async_call_with_json_kwargs(self, addon_instance: object, json_kwargs: dict):
