import enum

from django.core.exceptions import ValidationError

from addon_toolkit import AddonCapabilities
from addon_toolkit.interfaces.storage import StorageAddonImp

from . import known_imps
from .credentials_formats import CredentialsFormats
from .invocation_status import InvocationStatus
from .service_types import ServiceTypes


###
# validators for specific controlled vocabs


def validate_addon_capability(value):
    _validate_enum_value(AddonCapabilities, value)


def validate_invocation_status(value):
    _validate_enum_value(InvocationStatus, value)


def validate_service_type(value):
    _validate_enum_value(ServiceTypes, value)


def validate_credentials_format(value):
    _validate_enum_value(
        CredentialsFormats, value, excluded_members={CredentialsFormats.UNSPECIFIED}
    )


def validate_storage_imp_number(value):
    try:
        _imp_cls = known_imps.get_imp_by_number(value)
    except KeyError:
        raise ValidationError(f"invalid imp number: {value}")
    if not issubclass(_imp_cls, StorageAddonImp):
        raise ValidationError(f"expected storage imp (got {_imp_cls})")


###
# module-private helpers


def _validate_enum_value(enum_cls: type[enum.Enum], value, excluded_members=None):
    try:
        member = enum_cls(value)
    except ValueError:
        raise ValidationError(f'no value "{value}" in {enum_cls}')
    if excluded_members and member in excluded_members:
        raise ValidationError(
            f'"{member.name}" is not a supported value for this field'
        )
