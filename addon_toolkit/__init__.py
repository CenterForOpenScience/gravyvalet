"""
.. include:: README.md
"""

from . import (
    credentials,
    cursor,
    declarator,
    exceptions,
    iri_utils,
    json_arguments,
)
from .addon_operation_declaration import (
    AddonOperationDeclaration,
    AddonOperationType,
    addon_operation,
    eventual_operation,
    immediate_operation,
    redirect_operation,
)
from .addon_operation_results import RedirectResult
from .capabilities import AddonCapabilities
from .imp import AddonImp
from .interfaces import BaseAddonInterface


__all__ = (
    "AddonCapabilities",
    "AddonImp",
    "AddonOperationDeclaration",
    "AddonOperationType",
    "BaseAddonInterface",
    "RedirectResult",
    "addon_operation",
    "eventual_operation",
    "immediate_operation",
    "redirect_operation",
    # whole modules:
    "credentials",
    "cursor",
    "declarator",
    "exceptions",
    "iri_utils",
    "json_arguments",
)
