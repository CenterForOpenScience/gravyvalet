from addon_service.common.enums.validators import _validate_enum_value

from . import CredentialsFormats


def validate_credentials_format(value):
    _validate_enum_value(
        CredentialsFormats, value, excluded_members={CredentialsFormats.UNSPECIFIED}
    )
