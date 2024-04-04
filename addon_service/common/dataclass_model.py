import abc
from urllib.parse import (
    quote,
    unquote,
)

from addon_service.common.opaque import (
    make_opaque,
    unmake_opaque,
)


# abstract base class for dataclasses used as models
# (put duck-typing here for rest_framework_json_api)
class BaseDataclassModel(abc.ABC):
    ###
    # abstract methods

    @classmethod
    @abc.abstractmethod
    def get_by_natural_key(cls, *key_parts):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def natural_key(self) -> list:
        raise NotImplementedError

    ###
    # class methods

    @classmethod
    def get_by_pk(cls, pk: str):
        _natural_key_str = unmake_opaque(pk)
        return cls.get_by_natural_key_str(_natural_key_str)

    @classmethod
    def get_by_natural_key_str(cls, key_str: str):
        _key = tuple(unquote(_key_segment) for _key_segment in key_str.split(":"))
        return cls.get_by_natural_key(*_key)

    ###
    # instance methods

    @property
    def natural_key_str(self) -> str:
        return ":".join(quote(_key_segment) for _key_segment in self.natural_key)

    @property
    def pk(self) -> str:
        # duck-type django.db.Model.pk
        return make_opaque(self.natural_key_str)
