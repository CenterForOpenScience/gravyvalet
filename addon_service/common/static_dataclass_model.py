import abc
import typing

from addon_service.common.opaque import (
    make_opaque,
    unmake_opaque,
)
from addon_service.common.permacache_metaclass import PermacacheMetaclass


class StaticDataclassModel(metaclass=PermacacheMetaclass):
    """a django-model-like base class for statically defined, natural-keyed data
    (put duck-typing here for rest_framework_json_api)
    """

    ###
    # abstract methods

    @classmethod
    @abc.abstractmethod
    def init_args_from_static_key(cls, static_key: str) -> tuple:
        """return a tuple of positional args to be passed to this class's constructor"""
        raise NotImplementedError

    @property
    def static_key(self) -> str:
        raise NotImplementedError

    ###
    # class methods

    @classmethod
    def iter_all(cls) -> typing.Iterator[typing.Self]:
        """yield all available static instances of this class (if any)"""
        yield from ()  # optional override; default none

    @classmethod
    def get_by_pk(cls, pk: str) -> typing.Self:
        _static_key = unmake_opaque(pk)
        return cls.get_by_static_key(_static_key)

    @classmethod
    def get_by_static_key(cls, static_key: str) -> typing.Self:
        _init_args = cls.init_args_from_static_key(static_key)
        return cls(*_init_args)

    ###
    # instance methods

    @property
    def pk(self):
        return make_opaque(self.static_key)
