from rest_framework.serializers import (
    JSONField,
    ValidationError,
)

from addon_service.common.credentials_formats import CredentialsFormats
from addon_toolkit.exceptions import JsonArgumentsError
from addon_toolkit.json_arguments import dataclass_from_json


SUPPORTED_CREDENTIALS_FORMATS = set(CredentialsFormats) - {
    CredentialsFormats.UNSPECIFIED,
    CredentialsFormats.OAUTH2,
    CredentialsFormats.OAUTH1A,
}


class CredentialsField(JSONField):
    def __init__(self, write_only=True, required=False, *args, **kwargs):
        super().__init__(write_only=write_only, required=required)

    def to_internal_value(self, data):
        # this issue still hasn't been fixed on  FE, so keeping this for now
        if not data or not any(data.values()):
            return None  # consider empty {} same as omitting the field
        # No access to the credentials format here, so just try all of them
        for creds_format in SUPPORTED_CREDENTIALS_FORMATS:
            try:
                return dataclass_from_json(creds_format.dataclass, data)
            except JsonArgumentsError:
                pass
        raise ValidationError("Provided credentials do not match any known format")
