import dataclasses
from functools import cached_property

from addon_service.common import known_imps
from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    AddonOperationDeclaration,
    AddonOperationType,
)
from addon_toolkit.json_arguments import (
    jsonschema_for_dataclass,
    jsonschema_for_signature_params,
)


# dataclass wrapper for an operation implemented on a concrete AddonImp subclass
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonOperationModel(StaticDataclassModel):
    imp_cls: type[AddonImp]
    declaration: AddonOperationDeclaration

    ###
    # StaticDataclassModel abstract methods

    @classmethod
    def init_args_from_static_key(cls, static_key: str) -> tuple:
        (_imp_name, _operation_name) = static_key.split(":")
        _imp_cls = known_imps.get_imp_by_name(_imp_name)
        return (_imp_cls, _imp_cls.get_operation_declaration(_operation_name))

    @property
    def static_key(self) -> str:
        return ":".join((known_imps.get_imp_name(self.imp_cls), self.declaration.name))

    ###
    # fields for api

    @cached_property
    def name(self) -> str:
        return self.declaration.name

    @cached_property
    def operation_type(self) -> AddonOperationType:
        return self.declaration.operation_type

    @cached_property
    def docstring(self) -> str:
        return self.declaration.docstring

    @cached_property
    def implementation_docstring(self) -> str:
        return self.imp_cls.get_imp_function(self.declaration).__doc__ or ""

    @cached_property
    def capability(self) -> AddonCapabilities:
        return self.declaration.capability

    @cached_property
    def params_jsonschema(self) -> dict:
        return jsonschema_for_signature_params(self.declaration.call_signature)

    @cached_property
    def result_jsonschema(self) -> dict:
        return jsonschema_for_dataclass(self.declaration.result_dataclass)

    @cached_property
    def implemented_by(self):
        # local import to avoid circular import
        # (AddonOperationModel and AddonImpModel need to be mutually aware of each other in order to populate their respective relationship fields)
        from addon_service.addon_imp.models import AddonImpModel

        return AddonImpModel(self.imp_cls)

    class JSONAPIMeta:
        resource_name = "addon-operation-imps"
