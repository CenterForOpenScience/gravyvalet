import dataclasses
import enum
import inspect
import types
import typing


__all__ = (
    "kwargs_from_json",
    "json_for_typed_value",
    "jsonschema_for_annotation",
    "jsonschema_for_dataclass",
    "jsonschema_for_signature_params",
)


def jsonschema_for_signature_params(signature: inspect.Signature) -> dict:
    """build jsonschema corresponding to parameters from a function signature

    >>> def _foo(a: str, b: int = 7): ...
    >>> jsonschema_for_signature_params(inspect.signature(_foo))
    {'type': 'object',
     'properties': {'a': {'type': 'string'}, 'b': {'type': 'number'}},
     'required': ['a']}
    """
    return {
        "type": "object",
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
    """build jsonschema for a python type annotation"""
    if dataclasses.is_dataclass(annotation):
        return jsonschema_for_dataclass(annotation)
    if issubclass(annotation, enum.Enum):
        return {"enum": [_item.value for _item in annotation]}
    if annotation is str:
        return {"type": "string"}
    if annotation in (int, float):
        return {"type": "number"}
    if annotation in (tuple, list, set, frozenset):
        return {"type": "list"}
    raise NotImplementedError(f"what do with param annotation '{annotation}'?")


# TODO generic type: def json_for_typed_value[_ValueType: object](type_annotation: type[_ValueType], value: _ValueType):
def json_for_typed_value(type_annotation: typing.Any, value: typing.Any):
    """return json-serializable representation of field value

    >>> json_for_typed_value(int, 13)
    13
    >>> json_for_typed_value(str, 13)
    '13'
    >>> json_for_typed_value(list[int], [2,3,'7'])
    [2, 3, 7]
    """
    _is_optional, _type = _maybe_optional_type(type_annotation)
    if value is None:
        if not _is_optional:
            raise ValueError(f"got `None` for non-optional type {type_annotation}")
        return None
    if dataclasses.is_dataclass(_type):
        if not isinstance(value, _type):
            raise ValueError(f"expected instance of {_type}, got {value}")
        return json_for_dataclass(value)
    if issubclass(_type, enum.Enum):
        if value not in _type:
            raise ValueError(f"expected member of enum {_type}, got {value}")
        return value.value
    if _type in (str, int, float):  # check str before Iterable
        return _type(value)
    if isinstance(_type, types.GenericAlias):
        # parameterized generic like `list[int]`
        if issubclass(_type.__origin__, typing.Iterable):
            # iterables the only supported generic (...yet)
            try:
                (_item_annotation,) = _type.__args__
            except ValueError:
                pass
            else:
                return [
                    json_for_typed_value(_item_annotation, _item_value)
                    for _item_value in value
                ]
    raise NotImplementedError(f"what do with argument type {_type}? ({value=})")


def kwargs_from_json(
    signature: inspect.Signature,
    args_from_json: dict,
) -> dict:
    try:
        _kwargs = {
            _param_name: arg_value_from_json(
                signature.parameters[_param_name], _arg_value
            )
            for (_param_name, _arg_value) in args_from_json.items()
        }
        # use inspect.Signature.bind() (with dummy `self` value) to validate all required kwargs present
        _bound_kwargs = signature.bind(self=..., **_kwargs)
    except (TypeError, KeyError):
        raise ValueError(
            f"invalid json args for signature\n{signature=}\nargs={args_from_json}"
        )
    _bound_kwargs.arguments.pop("self")
    return _bound_kwargs.arguments


def arg_value_from_json(
    param: inspect.Parameter, json_arg_value: typing.Any
) -> typing.Any:
    if json_arg_value is None:
        return None  # TODO: check optional
    if dataclasses.is_dataclass(param.annotation):
        assert isinstance(json_arg_value, dict)
        return dataclass_from_json(param.annotation, json_arg_value)
    if issubclass(param.annotation, enum.Enum):
        return param.annotation(json_arg_value)
    if param.annotation in (tuple, list, set, frozenset):
        return param.annotation(json_arg_value)
    if param.annotation in (str, int, float):
        assert isinstance(json_arg_value, param.annotation)
        return json_arg_value
    raise NotImplementedError(f"what do with `{json_arg_value}` (value for {param})")


def json_for_dataclass(dataclass_instance) -> dict:
    """return json-serializable representation of the dataclass instance"""
    _field_value_pairs = (
        (_field, getattr(dataclass_instance, _field.name))
        for _field in dataclasses.fields(dataclass_instance)
    )
    return {
        _field.name: json_for_typed_value(_field.type, _value)
        for _field, _value in _field_value_pairs
        if (_value is not None) or (_field.default is not None)
    }


def dataclass_from_json(dataclass: type, dataclass_json: dict):
    return dataclass(
        **{
            _field.name: field_value_from_json(_field, dataclass_json)
            for _field in dataclasses.fields(dataclass)
        }
    )


def field_value_from_json(field: dataclasses.Field, dataclass_json: dict):
    _json_value = dataclass_json.get(field.name)
    if _json_value is None:
        return None  # TODO: check optional
    if dataclasses.is_dataclass(field.type):
        assert isinstance(_json_value, dict)
        return dataclass_from_json(field.type, _json_value)
    if issubclass(field.type, enum.Enum):
        return field.type(_json_value)
    if field.type in (tuple, list, set, frozenset):
        return field.type(_json_value)
    if field.type in (str, int, float):
        assert isinstance(_json_value, field.type)
        return _json_value
    raise NotImplementedError(f"what do with {_json_value=} (value for {field})")


def _maybe_optional_type(type_annotation: typing.Any) -> tuple[bool, typing.Any]:
    """given a type annotation, detect whether it allows `None` and extract the non-optional type

    >>> _maybe_optional_type(int)
    (False, <class 'int'>)
    >>> _maybe_optional_type(int | None)
    (True, <class 'int'>)
    >>> _maybe_optional_type(None)
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
