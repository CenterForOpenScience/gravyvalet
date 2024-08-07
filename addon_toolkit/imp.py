import functools
import inspect
import typing

from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)

from . import exceptions
from .addon_operation_declaration import AddonOperationDeclaration
from .capabilities import AddonCapabilities
from .interfaces import AddonInterface
from .json_arguments import kwargs_from_json


__all__ = ("AddonImp",)


class AddonImp:
    """base class for all addon implementations"""

    # subclasses must set `ADDON_INTERFACE`
    ADDON_INTERFACE: typing.ClassVar[type[AddonInterface]]

    ###
    # class methods

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not (
            hasattr(cls, "ADDON_INTERFACE")
            # AddonInterface is a typing.Protocol, but don't want duck-typing here
            and AddonInterface in cls.ADDON_INTERFACE.__mro__
        ):
            raise exceptions.ImpHasNoInterface(cls)

    @classmethod
    @functools.cache
    def all_implemented_operations(cls) -> frozenset[AddonOperationDeclaration]:
        return frozenset(
            _operation
            for _operation in cls.ADDON_INTERFACE.iter_declared_operations()
            if cls.has_implemented_operation(_operation)
        )

    @classmethod
    def implemented_operations_for_capabilities(
        cls, capabilities: AddonCapabilities
    ) -> typing.Iterator[AddonOperationDeclaration]:
        for _operation in cls.all_implemented_operations():
            if _operation.capability in capabilities:
                yield _operation

    @classmethod
    def has_implemented_operation(cls, operation: AddonOperationDeclaration):
        try:
            return bool(cls.get_imp_function(operation))
        except exceptions.OperationNotImplemented:
            return False

    @classmethod
    def get_imp_function(cls, operation: AddonOperationDeclaration):
        try:
            return getattr(cls, operation.name)
        except AttributeError:
            raise exceptions.OperationNotImplemented(cls, operation)

    @classmethod
    @functools.cache
    def get_operation_declaration(
        cls,
        operation_name: str,
        /,  # all args positional-only (for cache's sake)
    ) -> AddonOperationDeclaration:
        _operation = cls.ADDON_INTERFACE.get_operation_by_name(operation_name)
        if not cls.has_implemented_operation(_operation):
            raise exceptions.OperationNotImplemented(cls, _operation)
        return _operation

    @classmethod
    def confirm_credentials(cls, crendentials):
        pass

    ###
    # instance methods

    async def invoke_operation(
        self, operation: AddonOperationDeclaration, json_kwargs: dict
    ):
        _operation_method = getattr(self, operation.name)
        _kwargs = kwargs_from_json(operation.call_signature, json_kwargs)
        if not inspect.iscoroutinefunction(_operation_method):
            _operation_method = sync_to_async(_operation_method)
        _result = await _operation_method(**_kwargs)
        assert isinstance(_result, operation.result_dataclass)
        return _result

    invoke_operation__blocking = async_to_sync(invoke_operation)

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        """to be implemented by addons which require an external account id"""
        return ""
