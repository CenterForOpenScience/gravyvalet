

def immediate_capability(fn):
    return fn  # decorator stub


def proxy_capability(fn):
    return fn  # decorator stub


def redirect_capability(fn):
    return fn  # decorator stub


def action_capability(fn):
    return fn  # decorator stub


# def get_capability_method(interface_instance, capability_iri):
#     _methodname = _get_capability_method_map(interface_instance).get(capability_iri)
#     if _methodname is not None:
#         return getattr(interface_instance, _methodname)
#
#
# def _get_capability_method_map(obj):
#     try:
#         return getattr(obj, GRAVY.capability_map)
#     except AttributeError:
#         return _compute_capability_method_map(obj)
#
#
# def _compute_capability_method_map(obj):
#     _capability_method_map = {}
#     for _methodname, _method in inspect.getmembers(obj, inspect.ismethod):
#         try:
#             _capability_iri = getattr(_method, GRAVY.capability)
#         except AttributeError:
#             pass
#         else:
#             assert _capability_iri not in _capability_method_map
#             _capability_method_map[_capability_iri] = _methodname
#     setattr(obj, GRAVY.capability_map, _capability_method_map)
#     return _capability_method_map


# def _set_capability(capability_fn, capability_iri):
#     _prior_value = getattr(capability_fn, GRAVY.capability, None)
#     if _prior_value is not None:
#         raise ValueError
#     setattr(capability_fn, GRAVY.capability, capability_iri)
