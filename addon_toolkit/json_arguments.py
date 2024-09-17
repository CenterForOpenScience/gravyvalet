"""build and validate json kwargs from python type annotations
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import types
import typing
from collections import abc

from . import exceptions


__all__ = (
    "JsonschemaDocBuilder",
    "JsonschemaObjectBuilder",
    "dataclass_from_json",
    "json_for_dataclass",
    "json_for_kwargs",
    "json_for_typed_value",
    "kwargs_from_json",
    "typed_value_from_json",
)

###
# building jsonschema


@dataclasses.dataclass
class JsonschemaDocBuilder:
    """a dataclass for use while building a jsonschema document from python type annotations

    e.g. from a function signature

    >>> def _foo(a: str, b: int = 7): ...
    >>> JsonschemaDocBuilder(_foo).build()
    {'type': 'object',
     'additionalProperties': False,
     'properties': {'a': {'type': 'string'}, 'b': {'type': 'number'}},
     'required': ['a']}

    e.g. from dataclasses

    >>> @dataclasses.dataclass
    ... class _Foo:
    ...     a: str
    ...     b: int = 17
    ...
    >>> JsonschemaDocBuilder(_Foo).build()
    {'$ref': '#/$defs/addon_toolkit.json_arguments._Foo',
     '$defs': {'addon_toolkit.json_arguments._Foo':
        {'type': 'object',
        'additionalProperties': False,
        'properties': {'a': {'type': 'string'}, 'b': {'type': 'number'}},
        'required': ['a']}}}
    """

    annotated: typing.Any
    used_dataclasses: set[type] = dataclasses.field(default_factory=set)
    used_enums: set[type[enum.Enum]] = dataclasses.field(default_factory=set)

    def build(self) -> dict[str, typing.Any]:
        """get the built jsonschema as a json-serializable dictionary"""
        _built: dict[str, typing.Any] = {}
        if dataclasses.is_dataclass(self.annotated):
            _built["$ref"] = self.ref_for_dataclass(self.annotated)
        elif callable(self.annotated):
            _builder = JsonschemaObjectBuilder.for_kwargs(self.annotated, self)
            _built.update(_builder.build())
        _defs = self.build_defs()
        if _defs:
            _built["$defs"] = _defs
        return _built

    def build_defs(self) -> dict[str, dict]:
        _defs = {}
        # awkward loop because building one def may use additional dataclasses
        _todo = set(self.used_dataclasses)
        _done = set()
        while _todo:
            _dataclass = _todo.pop()
            if _dataclass not in _done:
                _builder = JsonschemaObjectBuilder.for_dataclass(_dataclass, self)
                _defs[self.def_key_for_type(_dataclass)] = _builder.build()
                _done.add(_dataclass)
                _todo.update(self.used_dataclasses - _done)
        for _enum in self.used_enums:
            _defs[self.def_key_for_type(_enum)] = {
                "enum": [_item.name for _item in _enum]
            }
        return _defs

    def def_key_for_type(self, some_type: type):
        return f"{some_type.__module__}.{some_type.__qualname__}"

    def ref_for_dataclass(self, dataclass: type) -> str:
        self.used_dataclasses.add(dataclass)
        return f"#/$defs/{self.def_key_for_type(dataclass)}"

    def ref_for_enum(self, enum: type) -> str:
        self.used_enums.add(enum)
        return f"#/$defs/{self.def_key_for_type(enum)}"


@dataclasses.dataclass
class JsonschemaObjectBuilder:
    """a dataclass for use while building a jsonschema (of type 'object') from python type annotations"""

    doc: JsonschemaDocBuilder | None
    property_annotations: dict[str, typing.Any] = dataclasses.field(
        default_factory=dict
    )
    required_property_names: set[str] = dataclasses.field(default_factory=set)
    self_type: type | None = None

    @classmethod
    def for_kwargs(
        cls, annotated_callable: typing.Any, doc: JsonschemaDocBuilder
    ) -> typing.Self:
        _signature = inspect.signature(annotated_callable)
        _annotations = inspect.get_annotations(annotated_callable, eval_str=True)
        return cls(
            doc=doc,
            property_annotations={
                _name: _annotation
                for (_name, _annotation) in _annotations.items()
                if _name not in ("self", "return")
            },
            required_property_names={
                _name
                for (_name, _param) in _signature.parameters.items()
                if _name != "self" and _param.default is inspect.Parameter.empty
            },
        )

    @classmethod
    def for_dataclass(cls, dataclass: type, doc: JsonschemaDocBuilder) -> typing.Self:
        """get a `JsonschemaObjectBuilder` for the constructor signature of a dataclass"""
        assert dataclasses.is_dataclass(dataclass) and isinstance(dataclass, type)
        _builder = cls.for_kwargs(dataclass, doc)
        _builder.self_type = dataclass
        return _builder

    def build(self) -> dict[str, typing.Any]:
        """get the built jsonschema as a json-serializable dictionary"""
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": self.build_properties(),
            "required": list(self.required_property_names),
        }

    def build_properties(self) -> dict[str, typing.Any]:
        return {
            _property_name: self._build_for_annotation(_annotation)
            for _property_name, _annotation in self.property_annotations.items()
        }

    def _build_for_annotation(self, annotation: type) -> dict:
        # ignore optional-ness here (handled by jsonschema "required")
        _type, _contained_type, _ = _unwrap_type(annotation, self_type=self.self_type)
        if _contained_type is not None:
            return {
                "type": "array",
                "items": self._build_for_annotation(_contained_type),
            }
        if dataclasses.is_dataclass(_type):
            assert self.doc is not None
            return {"$ref": self.doc.ref_for_dataclass(_type)}
        if isinstance(_type, type) and issubclass(_type, enum.Enum):
            assert self.doc is not None
            return {"$ref": self.doc.ref_for_enum(_type)}
        if _type is str:
            return {"type": "string"}
        if _type in (int, float):
            return {"type": "number"}
        if _type is dict:
            return {"type": "dict"}
        raise exceptions.TypeNotJsonable(_type)


###
# building json for types


# TODO generic type: def json_for_typed_value[_ValueType: object](type_annotation: type[_ValueType], value: _ValueType):
def json_for_typed_value(
    type_annotation: typing.Any,
    value: typing.Any,
    *,
    self_type: typing.Any = None,
):
    """return json-serializable representation of field value

    >>> json_for_typed_value(int, 13)
    13
    >>> json_for_typed_value(str, 13)
    '13'
    >>> json_for_typed_value(list[int], [2,3,'7'])
    [2, 3, 7]
    """
    _type, _contained_type, _is_optional = _unwrap_type(
        type_annotation, self_type=self_type
    )
    if value is None:
        if not _is_optional:
            raise exceptions.ValueNotJsonableWithType(value, type_annotation)
        return None
    if _type is typing.Any:
        return value
    if dataclasses.is_dataclass(_type):
        if isinstance(value, dict):
            return json_for_kwargs(_type, value)
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
    if _type is dict:
        if isinstance(value, dict):
            return {k: json_for_typed_value(typing.Any, v) for k, v in value.items()}
        raise exceptions.ValueNotJsonableWithType(value, _type)

    if _type is list:
        if isinstance(value, list):
            return [
                json_for_typed_value(_contained_type or typing.Any, _item_value)
                for _item_value in value
            ]
        raise exceptions.ValueNotJsonableWithType(value, _type)
    if (
        isinstance(_type, type)
        and issubclass(_type, abc.Collection)
        and _contained_type is not None
    ):
        return [
            json_for_typed_value(_contained_type, _item_value) for _item_value in value
        ]
    raise exceptions.ValueNotJsonableWithType(value, _type)


def json_for_kwargs(annotated_callable: abc.Callable, kwargs: dict) -> dict:
    """return json-serializable representation of the kwargs for the given signature"""
    _annotations = inspect.get_annotations(annotated_callable, eval_str=True)
    return {
        _keyword: json_for_typed_value(
            _annotation,
            kwargs[_keyword],
            self_type=annotated_callable,
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
    return json_for_kwargs(_dataclass, _kwargs)


###
# parsing json


def kwargs_from_json(
    annotated_callable: typing.Any,
    args_from_json: dict,
) -> dict:
    """parse json into python kwargs"""
    _signature = inspect.signature(annotated_callable)
    _annotations = inspect.get_annotations(annotated_callable)
    try:
        _kwargs = {
            _name: typed_value_from_json(
                _annotations[_name], _value, self_type=annotated_callable
            )
            for (_name, _value) in args_from_json.items()
        }
        # use inspect.Signature.bind() to validate all required kwargs present
        if "self" in _signature.parameters:
            _bound_kwargs = _signature.bind(self=..., **_kwargs)
            _bound_kwargs.arguments.pop("self", None)
        else:
            _bound_kwargs = _signature.bind(**_kwargs)
    except (TypeError, KeyError):
        raise exceptions.InvalidJsonArgsForSignature(args_from_json, _signature)
    return _bound_kwargs.arguments


def dataclass_from_json(dataclass: type, dataclass_json: dict):
    """parse json into an instance of the given dataclass"""
    _kwargs = kwargs_from_json(dataclass, dataclass_json)
    return dataclass(**_kwargs)


def typed_value_from_json(
    type_annotation: type, json_value: typing.Any, self_type: type | None = None
) -> typing.Any:
    """parse json into a python value of the given type"""
    _type, _contained_type, _is_optional = _unwrap_type(
        type_annotation, self_type=self_type
    )
    if json_value is None:
        if not _is_optional:
            raise exceptions.JsonValueInvalidForType(json_value, type_annotation)
        return None
    if dataclasses.is_dataclass(_type):
        if not isinstance(json_value, dict):
            raise exceptions.JsonValueInvalidForType(json_value, _type)
        return dataclass_from_json(_type, json_value)
    if isinstance(_type, type) and issubclass(_type, enum.Enum):
        return _type(json_value.lower() if isinstance(json_value, str) else json_value)
    if _type in (str, int, float):
        if not isinstance(json_value, _type):
            raise exceptions.JsonValueInvalidForType(json_value, _type)
        return json_value
    if _contained_type is not None and issubclass(_type, abc.Collection):
        _container_type = _type if issubclass(_type, (tuple, set, frozenset)) else list
        return _container_type(
            typed_value_from_json(
                _contained_type, _contained_value, self_type=self_type
            )
            for _contained_value in json_value
        )
    raise exceptions.TypeNotJsonable(_type)


###
# local helpers


def _unwrap_type(
    type_annotation: typing.Any, self_type: type | None = None
) -> tuple[type, typing.Any, bool]:
    """given a type annotation, unwrap into `(nongeneric_type, contained_type, is_optional)`

    >>> _unwrap_type(list[int])
    (<class 'list'>, <class 'int'>, False)
    >>> _unwrap_type(tuple[int] | None)
    (<class 'tuple'>, <class 'int'>, True)
    >>> _unwrap_type(str)
    (<class 'str'>, None, False)
    >>> _unwrap_type(float | None)
    (<class 'float'>, None, True)
    >>> _unwrap_type(list[typing.Self], self_type=int)
    (<class 'list'>, <class 'int'>, False)
    """
    _is_optional, _nonnone_type = _unwrap_optional_type(type_annotation)
    _nongeneric_type, _inner_item_type = _unwrap_generic_type(_nonnone_type)
    if _inner_item_type is typing.Self:
        _inner_item_type = self_type
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


def _unwrap_generic_type(type_annotation: typing.Any) -> tuple[type, typing.Any]:
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
