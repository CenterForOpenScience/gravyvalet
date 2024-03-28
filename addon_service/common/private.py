import weakref
from typing import ClassVar


__all__ = ("PrivateInfo",)


class PrivateInfo:
    """base class for conveniently assigning private info to an object

    >>> @dataclasses.dataclass
    >>> class _MyInfo(PrivateInfo):
    ...     foo: str
    >>> _rando = object()
    >>> _MyInfo('woo').assign(_rando)
    >>> _MyInfo.get(_rando)
    _MyInfo(foo='woo')
    """

    __private_map: ClassVar[weakref.WeakKeyDictionary]

    def __init_subclass__(cls):
        # each subclass gets its own private map -- this base class itself is unusable
        cls.__private_map = weakref.WeakKeyDictionary()

    @classmethod
    def get(cls, shared_obj: object):
        return cls.__private_map.get(shared_obj)

    def assign(self, shared_obj: object) -> None:
        self.__private_map[shared_obj] = self
