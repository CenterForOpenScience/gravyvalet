import dataclasses
import typing
from functools import cached_property

from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import (
    AddonCapabilities,
    AddonOperationDeclaration,
    AddonOperationType,
    interfaces,
)
from addon_toolkit.json_arguments import JsonschemaDocBuilder


# dataclass wrapper for an operation implemented on a concrete AddonImp subclass
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonOperationModel(StaticDataclassModel):
    interface_cls: type[interfaces.BaseAddonInterface]
    declaration: AddonOperationDeclaration

    ###
    # StaticDataclassModel abstract methods

    @classmethod
    def init_args_from_static_key(cls, static_key: str) -> tuple:
        (_interface_name, _operation_name) = static_key.split(":")
        _interface_cls = interfaces.AllAddonInterfaces[_interface_name].value
        return (_interface_cls, _interface_cls.get_operation_by_name(_operation_name))

    @classmethod
    def iter_all(cls) -> typing.Iterator[typing.Self]:
        """yield all available static instances of this class (if any)"""
        for _interface in interfaces.AllAddonInterfaces:
            _interface_cls = _interface.value
            for _operation_declaration in _interface_cls.iter_declared_operations():
                yield cls(_interface_cls, _operation_declaration)

    @property
    def static_key(self) -> str:
        return ":".join((self.interface_name, self.name))

    ###
    # fields for api

    @cached_property
    def name(self) -> str:
        return self.declaration.name

    @cached_property
    def interface_name(self) -> str:
        return interfaces.AllAddonInterfaces(self.interface_cls).name

    @cached_property
    def operation_type(self) -> AddonOperationType:
        return self.declaration.operation_type

    @cached_property
    def docstring(self) -> str:
        return self.declaration.docstring

    @cached_property
    def capability(self) -> AddonCapabilities:
        return self.declaration.capability

    @cached_property
    def kwargs_jsonschema(self) -> dict:
        return JsonschemaDocBuilder(self.declaration.operation_fn).build()

    @cached_property
    def result_jsonschema(self) -> dict:
        return JsonschemaDocBuilder(self.declaration.result_dataclass).build()

    @cached_property
    def implemented_by(self):
        # local import to avoid circular import
        # (AddonOperationModel and AddonImpModel need to be mutually aware of each other in order to populate their respective relationship fields)
        from addon_service.addon_imp.models import AddonImpModel

        _imps = set()
        for _imp_model in AddonImpModel.iter_all():
            if self.declaration in _imp_model.imp_cls.all_implemented_operations():
                _imps.add(_imp_model)
        return tuple(_imps)

    class JSONAPIMeta:
        resource_name = "addon-operations"
