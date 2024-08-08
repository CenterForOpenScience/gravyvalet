import uuid

from django.db import models


__all__ = (
    "StrUUIDField",
    "str_uuid4",
)


def str_uuid4() -> str:
    """generate a random UUID (as `str`)"""
    return str(uuid.uuid4())


class StrUUIDField(models.UUIDField):
    """same as UUIDField, but showing the string representation instead of uuid.UUID"""

    def get_prep_value(self, value):
        """parse `str` value as `uuid.UUID`"""
        _uuid = uuid.UUID(value) if isinstance(value, str) else value
        return super().get_prep_value(_uuid)

    def from_db_value(self, value, expression, connection):
        """convert `uuid.UUID` value to `str`"""
        return None if value is None else str(value)

    def to_python(self, value):
        """convert `uuid.UUID` value to `str`"""
        _uuid_value = super().to_python(value)
        return None if _uuid_value is None else str(_uuid_value)
