import dataclasses
import enum
import functools
import inspect
import typing
from http import HTTPMethod

from .capabilities import AddonCapabilities
from .declarator import Declarator


__all__ = (
    "AddonOperationDeclaration",
    "AddonOperationType",
    "addon_operation",
    "eventual_operation",
    "immediate_operation",
    "redirect_operation",
)


class AddonOperationType(enum.Enum):
    REDIRECT = "redirect"  # gravyvalet refers you somewhere helpful
    IMMEDIATE = "immediate"  # gravyvalet does a simple act, waiting to respond until done (success or problem)
    EVENTUAL = "eventual"  # gravyvalet starts a potentially long-running act, responding immediately with status


@dataclasses.dataclass(frozen=True)
class AddonOperationDeclaration:
    """dataclass for a declared operation method on an interface

    created by decorating a method with one of the "operation" decorators:
    `@redirect_operation`, `@immediate_operation`, `@eventual_operation`
    """

    operation_type: AddonOperationType
    capability: AddonCapabilities
    operation_fn: typing.Callable[..., typing.Any]  # the decorated function
    required_return_type: type | None = dataclasses.field(default=None, compare=False)

    @classmethod
    def for_function(
        self, fn: typing.Callable[..., typing.Any]
    ) -> "AddonOperationDeclaration":
        return addon_operation.get_declaration(fn)

    def __post_init__(self) -> None:
        if self.required_return_type and not issubclass(
            self.return_type, self.required_return_type
        ):
            raise ValueError(
                f"expected return type {self.return_type} on operation function {self.operation_fn} (got {self.return_type})"
            )

    @functools.cached_property
    def return_type(self) -> type:
        _return_type = self.call_signature.return_annotation
        if not (
            isinstance(_return_type, type) and dataclasses.is_dataclass(_return_type)
        ):
            raise ValueError(
                f"operation methods must return a dataclass (got {_return_type} on {self.operation_fn})"
            )
        return _return_type

    @property
    def name(self) -> str:
        # TODO: language tag (kwarg for tagged string?)
        return self.operation_fn.__name__

    @property
    def docstring(self) -> str:
        # TODO: language tag
        # TODO: docstring/description param on operation decorators, since __doc__ is removed on -O
        return self.operation_fn.__doc__ or ""

    @functools.cached_property
    def call_signature(self) -> inspect.Signature:
        return inspect.signature(self.operation_fn)


# declarator for all types of operations -- use operation_type-specific decorators below
addon_operation = Declarator(
    declaration_dataclass=AddonOperationDeclaration,
    field_for_target="operation_fn",
)


@dataclasses.dataclass
class RedirectResult:
    url: str
    method: HTTPMethod = HTTPMethod.GET


# decorator for operations that may be performed by a client request (e.g. redirect to waterbutler)
redirect_operation = addon_operation.with_kwargs(
    operation_type=AddonOperationType.REDIRECT,
    required_return_type=RedirectResult,
    # TODO: consider adding `save_invocation: bool = True`, set False here
)

# decorator for operations that must be performed by the server but should take only
# a short time, so a server may wait on the operation before responding to a request
# (e.g. get a metadata description of an item, list items in a given folder)
immediate_operation = addon_operation.with_kwargs(
    operation_type=AddonOperationType.IMMEDIATE,
)

# decorator for operations that must be performed by the server and may take a long time
# (e.g. move/copy file, archive file-tree, execute computation)
eventual_operation = addon_operation.with_kwargs(
    operation_type=AddonOperationType.EVENTUAL,
)
