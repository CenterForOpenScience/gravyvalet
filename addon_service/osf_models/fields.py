import datetime as dt
import json
from decimal import Decimal

import jwe
from dateutil.parser import isoparse
from django.contrib.postgres import lookups
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import JSONField
from django.forms import JSONField as JSONFormField

from app.settings import (
    OSF_SENSITIVE_DATA_SALT,
    OSF_SENSITIVE_DATA_SECRET,
)


SENSITIVE_DATA_KEY = jwe.kdf(
    OSF_SENSITIVE_DATA_SECRET.encode("utf-8"), OSF_SENSITIVE_DATA_SALT.encode("utf-8")
)


def ensure_bytes(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def ensure_str(value):
    if isinstance(value, bytes):
        return value.decode()
    return value


def encrypt_string(value, prefix="jwe:::") -> str:
    prefix = ensure_bytes(prefix)
    if value:
        _value_bytes = ensure_bytes(value)
        if _value_bytes and not _value_bytes.startswith(prefix):
            value = (prefix + jwe.encrypt(_value_bytes, SENSITIVE_DATA_KEY)).decode()
    return value


def decrypt_string(value, prefix="jwe:::") -> str:
    prefix = ensure_bytes(prefix)
    if value:
        _value_bytes = ensure_bytes(value)
        if _value_bytes.startswith(prefix):
            value = jwe.decrypt(
                _value_bytes[len(prefix):], SENSITIVE_DATA_KEY
            ).decode()
    return value


class EncryptedTextField(models.TextField):
    """
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    """

    prefix = "jwe:::"

    def get_db_prep_value(self, value, **kwargs):
        return encrypt_string(value, prefix=self.prefix)

    def to_python(self, value):
        return decrypt_string(value, prefix=self.prefix)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


class NonNaiveDateTimeField(models.DateTimeField):
    # It seems get_prep_value would not be called in gravyvalet because gv only reads from OSFDB
    def get_prep_value(self, value):
        value = super(NonNaiveDateTimeField, self).get_prep_value(value)
        if value is not None and (
            value.tzinfo is None or value.tzinfo.utcoffset(value) is None
        ):
            raise NaiveDatetimeException("Tried to encode a naive datetime.")
        return value


class NaiveDatetimeException(Exception):
    pass


class DateTimeAwareJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, dt.datetime):
            if o.tzinfo is None or o.tzinfo.utcoffset(o) is None:
                raise NaiveDatetimeException("Tried to encode a naive datetime.")
            return dict(type="encoded_datetime", value=o.isoformat())
        elif isinstance(o, dt.date):
            return dict(type="encoded_date", value=o.isoformat())
        elif isinstance(o, dt.time):
            if o.tzinfo is None or o.tzinfo.utcoffset(o) is None:
                raise NaiveDatetimeException("Tried to encode a naive time.")
            return dict(type="encoded_time", value=o.isoformat())
        elif isinstance(o, Decimal):
            return dict(type="encoded_decimal", value=str(o))
        return super(DateTimeAwareJSONEncoder, self).default(o)


def decode_datetime_objects(nested_value):
    if isinstance(nested_value, list):
        return [decode_datetime_objects(item) for item in nested_value]
    elif isinstance(nested_value, dict):
        for key, value in nested_value.items():
            if isinstance(value, dict) and "type" in value.keys():
                if value["type"] == "encoded_datetime":
                    nested_value[key] = isoparse(value["value"])
                if value["type"] == "encoded_date":
                    nested_value[key] = isoparse(value["value"]).date()
                if value["type"] == "encoded_time":
                    nested_value[key] = isoparse(value["value"]).time()
                if value["type"] == "encoded_decimal":
                    nested_value[key] = Decimal(value["value"])
            elif isinstance(value, dict):
                nested_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                nested_value[key] = decode_datetime_objects(value)
        return nested_value
    return nested_value


class DateTimeAwareJSONFormField(JSONFormField):

    def to_python(self, value):
        value = super(DateTimeAwareJSONFormField, self).to_python(value)
        try:
            return decode_datetime_objects(value)
        except TypeError:
            raise Exception()

    def prepare_value(self, value):
        try:
            return json.dumps(value, cls=DateTimeAwareJSONEncoder)
        except TypeError:
            raise Exception()


class DateTimeAwareJSONField(JSONField):

    def __init__(
        self, verbose_name=None, name=None, encoder=DateTimeAwareJSONEncoder, **kwargs
    ):
        super(DateTimeAwareJSONField, self).__init__(
            verbose_name, name, encoder, **kwargs
        )

    def formfield(self, **kwargs):
        defaults = {"form_class": DateTimeAwareJSONFormField}
        defaults.update(kwargs)
        return super(DateTimeAwareJSONField, self).formfield(**defaults)

    def from_db_value(self, value, expression, connection):
        value = super(DateTimeAwareJSONField, self).from_db_value(value, None, None)
        return decode_datetime_objects(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ("has_key", "has_keys", "has_any_keys"):
            return value
        return super(JSONField, self).get_prep_lookup(lookup_type, value)


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)
