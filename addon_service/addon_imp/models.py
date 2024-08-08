import dataclasses
import typing
from functools import cached_property

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import known_imps
from addon_service.common.static_dataclass_model import StaticDataclassModel
from addon_toolkit import AddonImp


@dataclasses.dataclass(frozen=True)
class AddonImpModel(StaticDataclassModel):
    """each `AddonImpModel` represents a statically defined subclass of `AddonImp`"""

    imp_cls: type[AddonImp]

    ###
    # StaticDataclassModel abstract methods

    @classmethod
    def init_args_from_static_key(cls, static_key: str) -> tuple:
        return (known_imps.get_imp_by_name(static_key),)

    @classmethod
    def iter_all(cls) -> typing.Iterator[typing.Self]:
        for _imp in known_imps.KnownAddonImps:
            yield cls(_imp.value)

    @property
    def static_key(self) -> str:
        return self.name

    ###
    # fields for api

    @cached_property
    def name(self) -> str:
        return known_imps.get_imp_name(self.imp_cls)

    @cached_property
    def imp_docstring(self) -> str:
        return self.imp_cls.__doc__ or ""

    @cached_property
    def interface_docstring(self) -> str:
        return self.imp_cls.ADDON_INTERFACE.__doc__ or ""

    @cached_property
    def implemented_operations(self) -> tuple[AddonOperationModel, ...]:
        return tuple(
            AddonOperationModel(self.imp_cls.ADDON_INTERFACE, _operation)
            for _operation in self.imp_cls.all_implemented_operations()
        )

    def get_operation_model(self, operation_name: str):
        return AddonOperationModel(
            self.imp_cls.ADDON_INTERFACE,
            self.imp_cls.get_operation_declaration(operation_name),
        )

    class JSONAPIMeta:
        resource_name = "addon-imps"
