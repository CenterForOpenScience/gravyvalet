import dataclasses
import enum
import inspect
from typing import (
    Iterable,
    Iterator,
)

from asgiref.sync import async_to_sync

from .json_arguments import kwargs_from_json
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
        for _declaration in self.addon_protocol.get_operation_declarations(
            capabilities=capabilities
        ):
            try:
                yield AddonOperationImp(addon_imp=self, declaration=_declaration)
            except NotImplementedError:  # TODO: helpful exception type
                pass  # operation not implemented

    def get_operation_imp_by_name(self, operation_name: str) -> "AddonOperationImp":
        try:
            return AddonOperationImp(
                addon_imp=self,
                declaration=self.addon_protocol.get_operation_declaration_by_name(
                    operation_name
                ),
            )
        except NotImplementedError:  # TODO: helpful exception type
            raise ValueError(f'unknown operation name "{operation_name}"')


@dataclasses.dataclass(frozen=True)
class AddonOperationImp:
    """dataclass for an operation implemented as part of an addon protocol implementation"""

    addon_imp: AddonImp
    declaration: AddonOperationDeclaration

    def __post_init__(self):
        _protocol_fn = getattr(
            self.addon_imp.addon_protocol.protocol_cls, self.declaration.name
        )
        if self.imp_function is _protocol_fn:
            raise NotImplementedError(  # TODO: helpful exception type
                f"operation '{self.declaration}' not implemented by {self.addon_imp}"
            )

    @property
    def imp_function(self):
        return getattr(self.addon_imp.imp_cls, self.declaration.name)

    def call_with_json_kwargs(self, addon_instance: object, json_kwargs: dict):
        _method = self._get_instance_method(addon_instance)
        if inspect.iscoroutinefunction(_method):
            _method = async_to_sync(_method)  # TODO: more async
        _result = _method(**self._get_kwargs(json_kwargs))
        assert isinstance(_result, self.declaration.return_dataclass)
        return _result

    def _get_instance_method(self, addon_instance: object):
        assert isinstance(addon_instance, self.addon_imp.imp_cls)
        return getattr(addon_instance, self.declaration.name)

    def _get_kwargs(self, json_kwargs: dict) -> dict:
        return kwargs_from_json(self.declaration.call_signature, json_kwargs)

    # TODO: async def async_call_with_json_kwargs(self, addon_instance: object, json_kwargs: dict):
