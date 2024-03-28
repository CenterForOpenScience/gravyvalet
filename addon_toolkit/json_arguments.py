import dataclasses
import enum
import inspect
import types
import typing


__all__ = (
    "kwargs_from_json",
    "dataclass_from_json",
    "json_for_arguments",
    "json_for_dataclass",
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


def json_for_arguments(bound_kwargs: inspect.BoundArguments) -> dict:
    """return json-serializable representation of the dataclass instance"""
    return {
        _param_name: json_for_typed_value(
            bound_kwargs.signature.parameters[_param_name].annotation,
            _arg_value,
        )
        for (_param_name, _arg_value) in bound_kwargs.arguments.items()
    }


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
    if value is None:
        # check type_annotation allows None
        assert isinstance(None, type_annotation), f"got {value=} with {type_annotation}"
        return None
    if dataclasses.is_dataclass(type_annotation):
        if not isinstance(value, type_annotation):
            raise ValueError(f"expected instance of {type_annotation}, got {value}")
        return json_for_dataclass(value)
    if issubclass(type_annotation, enum.Enum):
        if value not in type_annotation:
            raise ValueError(f"expected member of enum {type_annotation}, got {value}")
        return value.value
    if type_annotation in (str, int, float):  # check str before Iterable
        return type_annotation(value)
    # support parameterized generics like `list[int]`
    if isinstance(type_annotation, types.GenericAlias):
        if issubclass(type_annotation.__origin__, typing.Iterable):
            try:
                (_item_annotation,) = type_annotation.__args__
            except ValueError:
                pass
            else:
                return [
                    json_for_typed_value(_item_annotation, _item_value)
                    for _item_value in value
                ]
    raise NotImplementedError(
        f"what do with argument type {type_annotation}? ({value=})"
    )


def kwargs_from_json(
    signature: inspect.Signature,
    args_from_json: dict,
) -> dict:
    _kwargs = {
        _param_name: arg_value_from_json(signature.parameters[_param_name], _arg_value)
        for (_param_name, _arg_value) in args_from_json.items()
    }
    # use inspect.Signature.bind() to validate all required kwargs present
    return signature.bind(**_kwargs).kwargs


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
    return {
        _field.name: json_for_typed_value(
            _field.type, getattr(dataclass_instance, _field.name)
        )
        for _field in dataclasses.fields(dataclass_instance)
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
