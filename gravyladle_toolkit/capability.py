import inspect

from gravyvalet.namespaces import GRAVY


###
# ONE OPTION: use decorators to declare capability identifiers on interface methods

def immediate_capability(capability_iri, *, requires):
    # decorator for capabilities that can be computed immediately,
    # without sending any requests or waiting on external resources
    # (e.g. build a url in a known pattern or return declared static metadata)
    def _decorator(fn):
        # assert not async?
        _set_capability_iri(fn, capability_iri)
        return fn  # decorator stub (TODO: register someway addon_service can use it)

    return _decorator


def proxy_read_capability(capability_iri, *, requires):
    # decorator for capabilities that require fetching data from elsewhere,
    # but make no changes (e.g. get a metadata description of an item,
    # list items in a given folder)
    def _decorator(fn):
        return fn  # decorator stub (TODO)

    return _decorator


def proxy_act_capability(capability_iri, *, requires):
    # decorator for capabilities that initiate change, may take some time,
    # and may fail in strange ways (e.g. delete an item, copy a file tree)
    def _decorator(fn):
        return fn  # decorator stub (TODO)

    return _decorator


###
# helpers for capability methods

def get_supported_capabilities(interface):
    return set(_get_capability_method_map(interface).keys())


def get_capability_method(interface_instance, capability_iri):
    _methodname = _get_capability_method_map(interface_instance).get(capability_iri)
    if _methodname is not None:
        return getattr(interface_instance, _methodname)


###
# module-private helpers

def _get_capability_method_map(obj):
    try:
        return getattr(obj, GRAVY.capability_map)
    except AttributeError:
        return _compute_capability_method_map(obj)


def _compute_capability_method_map(obj):
    _capability_method_map = {}
    for _methodname, _fn in inspect.getmembers(obj, inspect.ismethod):
        try:
            _capability_iri = getattr(_fn, GRAVY.capability)
        except AttributeError:
            pass  # not a capability implementation
        else:
            assert _capability_iri not in _capability_method_map, (
                f'duplicate implementations of capability <{_capability_iri}>'
                f'(conflicting: {_fn}, {_capability_method_map[_capability_iri]})'
            )
            _capability_method_map[_capability_iri] = _methodname
    setattr(obj, GRAVY.capability_map, _capability_method_map)
    return _capability_method_map


def _get_capability_iri(fn):
    return getattr(fn, GRAVY.capability, None)


def _set_capability_iri(capability_fn, capability_iri):
    _prior_value = _get_capability_iri(capability_fn)
    if _prior_value is not None:
        raise ValueError
    setattr(capability_fn, GRAVY.capability, capability_iri)
