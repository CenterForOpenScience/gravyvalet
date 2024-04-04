import dataclasses
import enum

from addon_service.addon_imp.known import (
    get_imp_by_name,
    get_imp_name,
)
from addon_service.common.dataclass_model import BaseDataclassModel
from addon_toolkit import AddonOperationImp
from addon_toolkit.json_arguments import jsonschema_for_signature_params
from addon_toolkit.operation import AddonOperationType


# dataclass wrapper for addon_toolkit.AddonOperationImp that sufficiently
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass
class AddonOperationModel(BaseDataclassModel):
    operation_imp: AddonOperationImp

    @classmethod
    def get_by_natural_key(cls, imp_name, operation_name) -> "AddonOperationModel":
        _addon_imp = get_imp_by_name(imp_name)
        return cls(_addon_imp.get_operation_imp_by_name(operation_name))

    @property
    def natural_key(self) -> list:
        return [get_imp_name(self.operation_imp.addon_imp), self.name]

    @property
    def name(self) -> str:
        return self.operation_imp.operation.name

    @property
    def operation_type(self) -> AddonOperationType:
        return self.operation_imp.operation.operation_type

    @property
    def docstring(self) -> str:
        return self.operation_imp.operation.docstring

    @property
    def implementation_docstring(self) -> str:
        return self.operation_imp.imp_function.__doc__ or ""

    @property
    def capability(self) -> enum.Enum:
        return self.operation_imp.operation.capability

    @property
    def imp_cls(self) -> type:
        return self.operation_imp.addon_imp.imp_cls

    @property
    def implemented_by(self):
        # avoid circular import
        # (AddonOperationModel and AddonImpModel need to be mutually aware of each other in order to populate their respective relationship fields)
        from addon_service.addon_imp.models import AddonImpModel

        return AddonImpModel(self.operation_imp.addon_imp)

    @property
    def params_jsonschema(self) -> dict:
        return jsonschema_for_signature_params(
            self.operation_imp.operation.call_signature
        )

    class JSONAPIMeta:
        resource_name = "addon-operation-imps"
