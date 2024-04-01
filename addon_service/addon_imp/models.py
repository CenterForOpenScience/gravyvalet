import dataclasses

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.dataclass_model import BaseDataclassModel
from addon_toolkit import AddonImp

from .known import (
    get_imp_by_name,
    get_imp_name,
)


# dataclass wrapper for addon_toolkit.AddonImp that sufficiently
# meets rest_framework_json_api expectations on a model class
@dataclasses.dataclass(frozen=True)
class AddonImpModel(BaseDataclassModel):
    imp: AddonImp

    @classmethod
    def get_by_natural_key(cls, imp_name: str) -> "AddonImpModel":
        return cls(imp=get_imp_by_name(imp_name))

    @property
    def name(self) -> str:
        return get_imp_name(self.imp)

    @property
    def natural_key(self) -> list:
        return [self.name]

    @property
    def protocol_docstring(self) -> str:
        return self.imp.addon_protocol.protocol_cls.__doc__ or ""

    @property
    def imp_cls(self) -> type:
        return self.imp.imp_cls

    @property
    def imp_docstring(self) -> str:
        return self.imp.imp_cls.__doc__ or ""

    @property
    def implemented_operations(self) -> list[AddonOperationModel]:
        return [
            AddonOperationModel(_op_imp) for _op_imp in self.imp.get_operation_imps()
        ]

    def get_operation_imp(self, operation_name: str):
        return AddonOperationModel(self.imp.get_operation_imp_by_name(operation_name))

    class JSONAPIMeta:
        resource_name = "addon-imps"
