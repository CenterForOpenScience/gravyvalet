import dataclasses
import inspect
import logging
from http import HTTPMethod

import httpx  # TODO: reconsider new dependency

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)
from addon_toolkit.namespaces import GRAVY


__all__ = (  # public module attrs:
    "BaseAddonInterface",
    "immediate_capability",
    "proxy_read_capability",
    "proxy_act_capability",
)


_logger = logging.getLogger(__name__)


###
# decorators to declare capability identifiers on interface methods


def immediate_capability(capability_iri, *, requires):
    # decorator for capabilities that can be computed immediately,
    # without sending any requests or waiting on external resources
    # (e.g. build a url in a known pattern or return declared static metadata)
    def _decorator(fn):
        # TODO: helpful error messaging for implementers
        assert inspect.isfunction(fn)
        assert not inspect.isawaitable(fn)
        # TODO: assert based on `inspect.signature(fn).parameters`
        _set_capability_iri(fn, capability_iri)
        return fn  # decorator stub (TODO: register someway addon_service can use it)

    return _decorator


def proxy_read_capability(capability_iri, *, requires):
    # decorator for capabilities that require fetching data from elsewhere,
    # but make no changes (e.g. get a metadata description of an item,
    # list items in a given folder)
    def _decorator(fn):
        # TODO: assert based on `inspect.signature(fn)`
        assert inspect.isasyncgenfunction(fn)
        return fn

    return _decorator


def proxy_act_capability(capability_iri, *, requires):
    # decorator for capabilities that initiate change, may take some time,
    # and may fail in strange ways (e.g. delete an item, copy a file tree)
    def _decorator(fn):
        # TODO: assert based on `inspect.signature(fn)`
        return fn

    return _decorator


###
# addon interface


@dataclasses.dataclass
class BaseAddonInterface:
    ###
    # public api for use on `self` when implementing capabilities

    # TODO: consider intermediate dataclasses to limit direct use of data models
    authorized_account: AuthorizedStorageAccount
    configured_addon: ConfiguredStorageAddon | None

    async def send_request(self, http_method: HTTPMethod, url: str, **kwargs):
        """helper for external requests in addon implementations

        subclasses SHOULD use this instead of sending requests by hand
        """
        # TODO: common http handling (retry, backoff, etc) to ease implementer load
        _logger.info("sending %s to %s", http_method, url)
        async with httpx.AsyncClient() as _client:  # TODO: shared client?
            _response = await _client.request(
                http_method,
                url,
                **kwargs,
            )
            return _response

    ###
    # private api for capability book-keeping

    @classmethod
    def __declared_capabilities(cls):
        try:
            return cls.__declared_capabilities
        except AttributeError:
            _declared_capabilities = cls.__declared_capabilities = dict(
                cls.__iter_declared_capabilities()
            )
            return _declared_capabilities

    @classmethod
    def __iter_declared_capabilities(cls):
        for _methodname, _fn in inspect.getmembers(cls, inspect.ismethod):
            try:
                _capability_iri = _get_capability_iri(_fn)
            except AttributeError:
                pass
            else:  # is capability
                yield (_capability_iri, (_methodname, _fn))

        raise NotImplementedError  # TODO

    def __get_capability_method(self, capability_iri: str):
        _declared_capabilities = self.__declared_capabilities()
        try:
            _methodname, _fn = _declared_capabilities[capability_iri]
        except AttributeError:
            return NotImplemented
        # TODO: _method = getattr(...


###
# module-private helpers


def _get_capability_iri(fn):
    # may raise AttributeError
    return getattr(fn, GRAVY.capability)


def _set_capability_iri(capability_fn, capability_iri):
    try:
        _prior_value = _get_capability_iri(capability_fn)
    except AttributeError:
        _prior_value = None
    if _prior_value is not None:
        raise ValueError("cannot call _set_capability_iri twice (on %r)", capability_fn)
    setattr(capability_fn, GRAVY.capability, capability_iri)


def _get_capability_method_map(obj):
    try:
        return getattr(obj, GRAVY.capability_map)
    except AttributeError:
        return _compute_capability_method_map(obj)


def _compute_capability_method_map(obj):
    _capability_method_map = {}
    for _methodname, _fn in inspect.getmembers(obj, inspect.ismethod):
        # TODO: intent is to make it easy to implement the capabilities you are
        # trying to support while ignoring all the rest (until you want them).
        # on the base class, declare and decorate methods for each supported
        # capability, then implementers may implement (or not implement) any or
        # all of them -- this doesn't quite do all that, maybe try from __new__?
        try:
            _capability_iri = getattr(_fn, GRAVY.capability)
        except AttributeError:
            pass  # not a capability implementation
        else:
            assert _capability_iri not in _capability_method_map, (
                f"duplicate implementations of capability <{_capability_iri}>"
                f"(conflicting: {_fn}, {_capability_method_map[_capability_iri]})"
            )
            _capability_method_map[_capability_iri] = _methodname
    _logger.info("found capability methods on %r: %r", obj, _capability_method_map)
    setattr(obj, GRAVY.capability_map, _capability_method_map)
    return _capability_method_map
