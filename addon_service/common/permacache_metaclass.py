import functools
import logging


_logger = logging.getLogger(__name__)


class PermacacheMetaclass(type):
    """metaclass that caches new objects by constructor args -- same args get the same object

    careful: there's no cache size limit -- use only with bounded arg-space

    limitation: no keyword args; only positional args allowed
                (avoid duplicates from kwargs in different order)

    >>> class _MyCachedClass(metaclass=PermacacheMetaclass):
    ...     pass
    >>> _MyCachedClass() is _MyCachedClass()
    True

    """

    @functools.cache
    def __call__(cls, *args):
        _logger.debug("CachedByArgs: new %s with args=%r", cls, args)
        return super().__call__(*args)
