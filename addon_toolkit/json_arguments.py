import dataclasses
import enum
import inspect
import types
import typing
from collections import abc

from . import exceptions


__all__ = (
    "dataclass_from_json",
    "json_for_dataclass",
    "json_for_annotations_kwargs",
    "json_for_typed_value",
    "jsonschema_for_annotation",
    "jsonschema_for_dataclass",
    "jsonschema_for_signature_params",
    "kwargs_from_json",
    "typed_value_from_json",
)


###
# building jsonschema


def jsonschema_for_signature_params(signature: inspect.Signature) -> dict:
    """build jsonschema corresponding to parameters from a function signature

    >>> def _foo(a: str, b: int = 7): ...
    >>> jsonschema_for_signature_params(inspect.signature(_foo))
    {'type': 'object',
     'additionalProperties': False,
     'properties': {'a': {'type': 'string'}, 'b': {'type': 'number'}},
     'required': ['a']}
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            _param_name: jsonschema_for_annotation(_param.annotation)
            for (_param_name, _param) in signature.parameters.items()
            if _param_name != "self"
        },
        "required": [
            _param_name
            for (_param_name, _param) in signature.parameters.items()
            if (_param_name != "self") and (_param.default is inspect.Parameter.empty)
        ],
    }


def jsonschema_for_dataclass(dataclass: type) -> dict:
    """build jsonschema corresponding to the constructor signature of a dataclass"""
    assert dataclasses.is_dataclass(dataclass) and isinstance(dataclass, type)
    return jsonschema_for_signature_params(inspect.signature(dataclass))


def jsonschema_for_annotation(annotation: type) -> dict:
    """build jsonschema for a python type annotation

    >>> jsonschema_for_annotation(str)
    {'type': 'string'}
    >>> jsonschema_for_annotation(int)
    {'type': 'number'}

    support generic collections (as json arrays)
    >>> jsonschema_for_annotation(list[int])
    {'type': 'array', 'items': {'type': 'number'}}
    >>> jsonschema_for_annotation(tuple[str])
    {'type': 'array', 'items': {'type': 'string'}}

    support enums (using enum name as string)
    >>> from http import HTTPMethod
    >>> jsonschema_for_annotation(HTTPMethod)
    {'enum': ['CONNECT', 'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'TRACE']}
    """
    # ignore optional-ness here (handled by jsonschema "required")
    _type, _contained_type, _ = _unwrap_type(annotation)
    if dataclasses.is_dataclass(_type):
        return jsonschema_for_dataclass(_type)
    if issubclass(_type, enum.Enum):
        return {"enum": [_item.name for _item in _type]}
    if _type is str:
        return {"type": "string"}
    if _type in (int, float):
        return {"type": "number"}
    if issubclass(_type, abc.Collection):
        _array_jsonschema: dict[str, typing.Any] = {"type": "array"}
        if _contained_type is not None:
            _array_jsonschema["items"] = jsonschema_for_annotation(_contained_type)
        return _array_jsonschema
    raise exceptions.TypeNotJsonable(_type)


###
# building json for types


# TODO generic type: def json_for_typed_value[_ValueType: object](type_annotation: type[_ValueType], value: _ValueType):
def json_for_typed_value(
    type_annotation: typing.Any, value: typing.Any, *, self_type: typing.Any = None
):
    """return json-serializable representation of field value

    >>> json_for_typed_value(int, 13)
    13
    >>> json_for_typed_value(str, 13)
    '13'
    >>> json_for_typed_value(list[int], [2,3,'7'])
    [2, 3, 7]
    """
    _type, _contained_type, _is_optional = _unwrap_type(type_annotation)
    if (self_type is not None) and (_contained_type is typing.Self):
        _contained_type = self_type
    if value is None:
        if not _is_optional:
            raise exceptions.ValueNotJsonableWithType(value, type_annotation)
        return None
    if dataclasses.is_dataclass(_type):
        if isinstance(value, dict):
            return json_for_annotations_kwargs(_type, value)
        if isinstance(value, _type):
            return json_for_dataclass(value)
        raise exceptions.ValueNotJsonableWithType(value, _type)
    if isinstance(_type, type) and issubclass(_type, enum.Enum):
        if value not in _type:
            raise exceptions.ValueNotJsonableWithType(value, _type)
        return value.name
    if _type in (str, int, float):  # check str before abc.Collection
        if not isinstance(value, (str, int, float)):
            raise exceptions.ValueNotJsonableWithType(value, _type)
        assert issubclass(_type, (str, int, float))  # assertion for type-checker
        return _type(value)
    if (
        isinstance(_type, type)
        and issubclass(_type, abc.Collection)
        and _contained_type is not None
    ):
        return [
            json_for_typed_value(_contained_type, _item_value) for _item_value in value
        ]
    raise exceptions.ValueNotJsonableWithType(value, _type)


def json_for_annotations_kwargs(annotations_subject: typing.Any, kwargs: dict) -> dict:
    """return json-serializable representation of the kwargs for the given signature"""
    _annotations = inspect.get_annotations(annotations_subject)
    return {
        _keyword: json_for_typed_value(
            _annotation,
            kwargs[_keyword],
            self_type=annotations_subject,
        )
        for (_keyword, _annotation) in _annotations.items()
        if _keyword in kwargs
    }


def json_for_dataclass(dataclass_instance) -> dict:
    """return json-serializable representation of the dataclass instance"""
    _dataclass = dataclass_instance.__class__
    _kwargs: dict = {}
    for _field in dataclasses.fields(dataclass_instance):
        _field_value = getattr(dataclass_instance, _field.name)
        if _field_value != _field.default:
            _kwargs[_field.name] = _field_value
    return json_for_annotations_kwargs(_dataclass, _kwargs)


###
# parsing json


def kwargs_from_json(
    signature: inspect.Signature,
    args_from_json: dict,
) -> dict:
    try:
        _kwargs = {
            _param_name: typed_value_from_json(
                signature.parameters[_param_name].annotation, _arg_value
            )
            for (_param_name, _arg_value) in args_from_json.items()
        }
        # use inspect.Signature.bind() to validate all required kwargs present
        if "self" in signature.parameters:
            _bound_kwargs = signature.bind(self=..., **_kwargs)
            _bound_kwargs.arguments.pop("self", None)
        else:
            _bound_kwargs = signature.bind(**_kwargs)
    except (TypeError, KeyError):
        raise exceptions.InvalidJsonArgsForSignature(args_from_json, signature)
    return _bound_kwargs.arguments


def typed_value_from_json(type_annotation: type, json_value: typing.Any) -> typing.Any:
    _type, _contained_type, _is_optional = _unwrap_type(type_annotation)
    if json_value is None:
        if not _is_optional:
            raise exceptions.JsonValueInvalidForType(json_value, type_annotation)
        return None
    if dataclasses.is_dataclass(_type):
        if not isinstance(json_value, dict):
            raise exceptions.JsonValueInvalidForType(json_value, _type)
        return dataclass_from_json(_type, json_value)
    if issubclass(_type, enum.Enum):
        return _type(json_value)
    if _type in (str, int, float):
        if not isinstance(json_value, _type):
            raise exceptions.JsonValueInvalidForType(json_value, _type)
        return json_value
    if _contained_type is not None and issubclass(_type, abc.Collection):
        _container_type = _type if issubclass(_type, (tuple, set, frozenset)) else list
        return _container_type(
            typed_value_from_json(_contained_type, _contained_value)
            for _contained_value in json_value
        )
    raise exceptions.TypeNotJsonable(_type)


def dataclass_from_json(dataclass: type, dataclass_json: dict):
    _kwargs = kwargs_from_json(inspect.signature(dataclass), dataclass_json)
    return dataclass(**_kwargs)


###
# local helpers


def _unwrap_type(type_annotation: typing.Any) -> tuple[type, typing.Any, bool]:
    """given a type annotation, unwrap into `(nongeneric_type, contained_type, is_optional)`

    >>> _unwrap_type(list[int])
    (<class 'list'>, <class 'int'>, False)
    >>> _unwrap_type(tuple[int] | None)
    (<class 'tuple'>, <class 'int'>, True)
    >>> _unwrap_type(str)
    (<class 'str'>, None, False)
    >>> _unwrap_type(float | None)
    (<class 'float'>, None, True)
    """
    _is_optional, _nonnone_type = _unwrap_optional_type(type_annotation)
    _nongeneric_type, _inner_item_type = _unwrap_generic_type(_nonnone_type)
    return (_nongeneric_type, _inner_item_type, _is_optional)


def _unwrap_optional_type(type_annotation: typing.Any) -> tuple[bool, typing.Any]:
    """given a type annotation, detect whether it allows `None` and extract the non-optional type

    >>> _unwrap_optional_type(int)
    (False, <class 'int'>)
    >>> _unwrap_optional_type(int | None)
    (True, <class 'int'>)
    >>> _unwrap_optional_type(None)
    (True, None)
    """
    if isinstance(type_annotation, types.UnionType):
        _allows_none = type(None) in type_annotation.__args__
        _nonnone_types = [
            _alt_type
            for _alt_type in type_annotation.__args__
            if _alt_type is not type(None)
        ]
        _base_type = (
            _nonnone_types[0]
            if len(_nonnone_types) == 1
            else types.UnionType(*_nonnone_types)
        )
    else:
        _allows_none = type_annotation is None
        _base_type = type_annotation
    return (_allows_none, _base_type)


def _unwrap_generic_type(type_annotation: typing.Any) -> tuple[type, type | None]:
    """given a type annotation, detect whether it's a generic collection
    and split the collection type from the item type

    >>> _unwrap_generic_type(int)
    (<class 'int'>, None)
    >>> _unwrap_generic_type(list[int])
    (<class 'list'>, <class 'int'>)
    >>> _unwrap_generic_type(abc.Sequence[str])
    (<class 'collections.abc.Sequence'>, <class 'str'>)
    """
    _unwrapped_type = type_annotation
    _item_annotation = None
    # support list-like collections as parameterized generic types
    if isinstance(type_annotation, types.GenericAlias):
        _unwrapped_type = type_annotation.__origin__
        # parameterized generic like `list[int]` or `abc.Sequence[ItemResult]`
        if issubclass(_unwrapped_type, abc.Collection):
            try:
                (_item_annotation,) = type_annotation.__args__
            except ValueError:
                raise exceptions.TypeNotJsonable(type_annotation)
        else:
            raise exceptions.TypeNotJsonable(type_annotation)
    return (_unwrapped_type, _item_annotation)
