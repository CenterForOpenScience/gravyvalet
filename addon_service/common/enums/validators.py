from django.core.exceptions import ValidationError

from addon_service.addon_imp.known import get_imp_by_number
from addon_service.common.invocation import InvocationStatus
from addon_toolkit import AddonCapabilities
from addon_toolkit.storage import StorageAddon


###
# validators for specific controlled vocabs


def validate_addon_capability(value):
    _validate_enum_value(AddonCapabilities, value)


def validate_invocation_status(value):
    _validate_enum_value(InvocationStatus, value)


def validate_storage_imp_number(value):
    try:
        _imp = get_imp_by_number(value)
    except KeyError:
        raise ValidationError(f"invalid imp number: {value}")
    if _imp.addon_protocol.protocol_cls is not StorageAddon:
        raise ValidationError(f"expected storage imp (got {_imp})")


###
# module-local helpers


def _validate_enum_value(enum_cls, value):
    try:
        enum_cls(value)
    except ValueError:
        raise ValidationError(f'no value "{value}" in {enum_cls}')
