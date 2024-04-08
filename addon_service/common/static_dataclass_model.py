import abc
import dataclasses
import typing
import weakref
from urllib.parse import (
    quote,
    unquote,
)

from addon_service.common.opaque import (
    make_opaque,
    unmake_opaque,
)


NATURAL_KEY_DELIMITER = ":"


class StaticDataclassModel(abc.ABC):
    """a django-model-like base class for statically defined, natural-keyed data
    (put duck-typing here for rest_framework_json_api)
    """

    ###
    # abstract methods

    @classmethod
    @abc.abstractmethod
    def do_get_by_natural_key(cls, *key_parts) -> typing.Self:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def natural_key(self) -> tuple[str, ...]:
        raise NotImplementedError

    ###
    # class methods

    @classmethod
    def get_by_pk(cls, pk: str):
        _natural_key_str = unmake_opaque(pk)
        return cls.get_by_natural_key_str(_natural_key_str)

    @classmethod
    def get_by_natural_key_str(cls, key_str: str):
        _key_parts = tuple(
            unquote(_key_segment)
            for _key_segment in key_str.split(NATURAL_KEY_DELIMITER)
        )
        return cls.get_by_natural_key(*_key_parts)

    @classmethod
    def get_by_natural_key(cls, *key_parts) -> typing.Self:
        """get the static model instance for the given key

        runs `do_get_by_natural_key` once per natural key, caches result until app restart
        """
        _cache = _StaticCache.for_class(cls)
        try:
            _gotten = _cache.by_natural_key[key_parts]
        except KeyError:
            _gotten = cls.do_get_by_natural_key(*key_parts)
            # should already be cached, via __post_init__
            assert _cache.by_natural_key[key_parts] == _gotten
        return _gotten

    ###
    # instance methods

    def __post_init__(self):
        self.encache_self()

    @property
    def natural_key_str(self) -> str:
        return NATURAL_KEY_DELIMITER.join(
            quote(_key_segment) for _key_segment in self.natural_key
        )

    @property
    def pk(self) -> str:
        # duck-type django.db.Model.pk
        return make_opaque(self.natural_key_str)

    def encache_self(self: typing.Self) -> None:
        _cache = _StaticCache.for_class(self.__class__)
        _cache.by_natural_key[self.natural_key] = self


# private caching helper


@dataclasses.dataclass
class _StaticCache:
    by_natural_key: dict[tuple[str, ...], typing.Any] = dataclasses.field(
        default_factory=dict
    )
    __caches_by_class: typing.ClassVar[
        weakref.WeakKeyDictionary[type, "_StaticCache"]
    ] = weakref.WeakKeyDictionary()

    @staticmethod
    def for_class(any_class: type) -> "_StaticCache":
        try:
            return _StaticCache.__caches_by_class[any_class]
        except KeyError:
            _new = _StaticCache()
            _StaticCache.__caches_by_class[any_class] = _new
            return _new
