import dataclasses

from django.utils.functional import cached_property

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import AddonImp

from .known import (
    get_imp_by_name,
    get_imp_name,
)


# dataclass wrapper for addon_toolkit.AddonImp that sufficiently
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonImpModel(StaticDataclassModel):
    imp: AddonImp

    ###
    # class methods

    @classmethod
    def do_get_by_natural_key(cls, *key_parts) -> "AddonImpModel":
        (_imp_name,) = key_parts
        return cls(get_imp_by_name(_imp_name))

    @classmethod
    def get_model_for_imp(cls, imp: AddonImp):
        return cls.get_by_natural_key(get_imp_name(imp))

    @cached_property
    def protocol_docstring(self) -> str:
        return self.imp.addon_protocol.protocol_cls.__doc__ or ""

    ###
    # instance methods

    @cached_property
    def name(self) -> str:
        return get_imp_name(self.imp)

    @cached_property
    def imp_cls(self) -> type:
        return self.imp.imp_cls

    @cached_property
    def imp_docstring(self) -> str:
        return self.imp.imp_cls.__doc__ or ""

    @cached_property
    def implemented_operations(self) -> frozenset[AddonOperationModel]:
        return frozenset(
            AddonOperationModel.get_model_for_operation_imp(_op_imp)
            for _op_imp in self.imp.get_operation_imps()
        )

    @property
    def natural_key(self) -> tuple[str, ...]:
        return (self.name,)

    def get_operation_imp(self, operation_name: str):
        return AddonOperationModel.get_model_for_operation_imp(
            self.imp.get_operation_imp_by_name(operation_name)
        )

    class JSONAPIMeta:
        resource_name = "addon-imps"
