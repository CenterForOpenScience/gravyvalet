import dataclasses
from functools import cached_property

from addon_service.addon_imp.known import (
    get_imp_by_name,
    get_imp_name,
)
from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import (
    AddonCapabilities,
    AddonOperationImp,
)
from addon_toolkit.json_arguments import (
    JsonableDict,
    jsonschema_for_signature_params,
)
from addon_toolkit.operation import AddonOperationType


# dataclass wrapper for addon_toolkit.AddonOperationImp that sufficiently
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonOperationModel(StaticDataclassModel):
    operation_imp: AddonOperationImp

    @classmethod
    def get_model_for_operation_imp(cls, operation_imp: AddonOperationImp):
        return cls.get_by_natural_key(
            get_imp_name(operation_imp.addon_imp),
            operation_imp.declaration.name,
        )

    @cached_property
    def name(self) -> str:
        return self.operation_imp.declaration.name

    @cached_property
    def operation_type(self) -> AddonOperationType:
        return self.operation_imp.declaration.operation_type

    @cached_property
    def docstring(self) -> str:
        return self.operation_imp.declaration.docstring

    @cached_property
    def implementation_docstring(self) -> str:
        return self.operation_imp.imp_function.__doc__ or ""

    @cached_property
    def capability(self) -> AddonCapabilities:
        return self.operation_imp.declaration.capability

    @cached_property
    def params_jsonschema(self) -> JsonableDict:
        return jsonschema_for_signature_params(
            self.operation_imp.declaration.call_signature
        )

    @cached_property
    def implemented_by(self):
        # local import to avoid circular import
        # (AddonOperationModel and AddonImpModel need to be mutually aware of each other in order to populate their respective relationship fields)
        from addon_service.addon_imp.models import AddonImpModel

        return AddonImpModel.get_model_for_imp(self.operation_imp.addon_imp)

    @classmethod
    def do_get_by_natural_key(cls, *key_parts) -> "AddonOperationModel":
        (_imp_name, _operation_name) = key_parts
        _addon_imp = get_imp_by_name(_imp_name)
        return cls(operation_imp=_addon_imp.get_operation_imp_by_name(_operation_name))

    @property
    def natural_key(self) -> tuple[str, ...]:
        return (
            get_imp_name(self.operation_imp.addon_imp),
            self.name,
        )

    class JSONAPIMeta:
        resource_name = "addon-operation-imps"
