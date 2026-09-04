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
from .json_arguments import kwargs_from_json


if typing.TYPE_CHECKING:
    from .interfaces import BaseAddonInterface


__all__ = ("AddonImp",)


class AddonImp:
    """base class for all addon implementations"""

    # subclasses must set `ADDON_INTERFACE`
    ADDON_INTERFACE: "typing.ClassVar[type[BaseAddonInterface]]"

    ###
    # class methods

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
    def confirm_credentials(cls, credentials): ...

    ###
    # instance methods

    async def invoke_operation(
        self, operation: AddonOperationDeclaration, json_kwargs: dict
    ):
        """try to run an operation on this imp"""
        _operation_method = getattr(self, operation.name)
        _kwargs = kwargs_from_json(operation.operation_fn, json_kwargs)
        if not inspect.iscoroutinefunction(_operation_method):
            _operation_method = sync_to_async(_operation_method)
        _result = await _operation_method(**_kwargs)
        assert isinstance(
            _result, operation.result_dataclass
        ), f"expected {operation.result_dataclass.__name__} type to be returned from method {_operation_method.__name__}, got {_result.__class__.__name__}"
        return _result

    invoke_operation__blocking = async_to_sync(invoke_operation)
    """try to run an operation on this imp (and wait until done)"""

    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        """to be implemented by addons which require an external account id"""
        return ""
