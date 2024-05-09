import dataclasses

from django.utils.functional import cached_property

from addon_service.addon_imp.known import (
    get_imp_by_name,
)
from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import AddonOperationImp
from addon_toolkit.json_arguments import jsonschema_for_signature_params
from addon_toolkit.operation import AddonOperationType


# dataclass wrapper for addon_toolkit.AddonOperationImp that sufficiently
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonOperationModel(StaticDataclassModel):
    operation_imp: AddonOperationImp

    def __new__(cls, operation_imp):
        return super().__new__(cache_key=operation_imp.natural_key, operation_imp=opeartion_imp)

    @classmethod
    def from_natural_key(cls, *key_parts: tuple[str, ...]) -> AddonOperationModel:
        try:
            super().get_by_natural_key(key_parts)
        except KeyError:
             (_addon_imp_name, _operation_name) = key_parts
             _addon_imp = get_imp_by_name(_addon_imp_name)
             retun cls(_addon_imp.get_operation_imp_by_name(_operation_name))

    @cached_property
    def name(self) -> str:
        return self.operation_imp.declaration.name

    @property
    def natural_key(self) -> tuple[str, ...]:
        return self.operation_imp.natural_key

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
    def capability(self) -> str:
        return self.operation_imp.declaration.capability

    @cached_property
    def params_jsonschema(self) -> dict:
        return jsonschema_for_signature_params(
            self.operation_imp.declaration.call_signature
        )

    @cached_property
    def implemented_by(self):
        # local import to avoid circular import
        # (AddonOperationModel and AddonImpModel need to be mutually aware of each other in order to populate their respective relationship fields)
        from addon_service.addon_imp.models import AddonImpModel

        return AddonImpModel(self.operation_imp.addon_imp)


    class JSONAPIMeta:
        resource_name = "addon-operation-imps"
