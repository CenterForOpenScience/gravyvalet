"""declarator: "declarative" + "decorator"

define a dataclass with fields you want declared in your decorator, plus a field
to hold the subject of declaration:
>>> @dataclasses.dataclass
... class TwoPartGreetingDeclaration:
...     a: str
...     b: str
...     on: object

use that dataclass to define a `Declarator`:
>>> greet = Declarator(TwoPartGreetingDeclaration, field_for_subject='on')

call the declarator with kwargs for the remaining dataclass fields
and use it as a decorator to create a declaration:
>>> @greet(a='hey', b='hello')
... def _hihi():
...     pass

use the declarator to access declarations by subject:
>>> greet.get_declaration(_hihi)
TwoPartGreetingDeclaration(a='hey', b='hello', on=<function _hihi at 0x...>)

use `.with_kwargs` to create aliased decorators with static values:
>>> ora = greet.with_kwargs(b='ora')
>>> @ora(a='kia')
... def _kia_ora():
...     pass

and find that aliased decoration via the original declarator:
>>> greet.get_declaration(_kia_ora)
TwoPartGreetingDeclaration(a='kia', b='ora', on=<function _kia_ora at 0x...>)
"""

import dataclasses
import weakref
from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
)


DecoratorSubject = TypeVar("DecoratorSubject")
DeclarationDataclass = TypeVar("DeclarationDataclass")


@dataclasses.dataclass
class Declarator(Generic[DeclarationDataclass]):
    """Declarator: declarative metadata using decorators and dataclasses"""

    declaration_dataclass: type[DeclarationDataclass]
    field_for_subject: str
    static_kwargs: dict[str, Any] | None = None

    # private storage linking a decorated class or function to data gleaned from its decorator
    __declarations_by_subject: weakref.WeakKeyDictionary[
        object, DeclarationDataclass
    ] = dataclasses.field(
        default_factory=weakref.WeakKeyDictionary,
    )

    def __post_init__(self) -> None:
        assert dataclasses.is_dataclass(
            self.declaration_dataclass
        ), f"expected dataclass, got {self.declaration_dataclass}"
        assert any(
            _field.name == self.field_for_subject
            for _field in dataclasses.fields(self.declaration_dataclass)
        ), f'expected field "{self.field_for_subject}" on dataclass "{self.declaration_dataclass}"'

    def __call__(
        self, **declaration_dataclass_kwargs
    ) -> Callable[[DecoratorSubject], DecoratorSubject]:
        """for using a Declarator as a decorator"""

        def _decorator(decorator_subject: DecoratorSubject) -> DecoratorSubject:
            self.set_declaration(decorator_subject, **declaration_dataclass_kwargs)
            return decorator_subject

        return _decorator

    def with_kwargs(self, **static_kwargs) -> "Declarator":
        """convenience for decorators that differ only by static field values"""
        # note: shared __declarations_by_subject
        return dataclasses.replace(self, static_kwargs=static_kwargs)

    def set_declaration(
        self, declaration_subject: DecoratorSubject, **declaration_dataclass_kwargs
    ) -> None:
        """create a declaration associated with the subject

        has the same effect as using the declarator as a decorator with the given kwargs
        """
        # dataclass validates decorator kwarg names
        self.__declarations_by_subject[declaration_subject] = (
            self.declaration_dataclass(
                **declaration_dataclass_kwargs,
                **(self.static_kwargs or {}),
                **{self.field_for_subject: declaration_subject},
            )
        )

    def get_declaration(self, subject) -> DeclarationDataclass:
        try:
            return self.__declarations_by_subject[subject]
        except KeyError:
            raise ValueError(f"no declaration found for {subject}")


class ClassDeclarator(Declarator):
    """add declarative metadata to python classes using decorators

    (same as Declarator but with additional methods that only make
    sense when used to decorate classes, and allow for inheritance
    and class instances)

    example declaration dataclass:
    >>> @dataclasses.dataclass
    ... class SemanticVersionDeclaration:
    ...     major: int
    ...     minor: int
    ...     patch: int
    ...     subj: type

    with shorthand declarator:
    >>> semver = ClassDeclarator(SemanticVersionDeclaration, field_for_subject='subj')

    for declarating classes:
    >>> @semver(
    ...   major=4,
    ...   minor=2,
    ...   patch=9,
    ... )
    ... class MyLongLivedBaseClass:
    ...     pass

    can get that declaration on the decorated class directly
    >>> semver.get_declaration(MyLongLivedBaseClass)
    SemanticVersionDeclaration(major=4, minor=2, patch=9, subj=<class 'addon_toolkit.declarator.MyLongLivedBaseClass'>)

    but `get_declaration` recognizes only the exact decorated subject, not an instance or subclass:
    >>> semver.get_declaration(MyLongLivedBaseClass())
    Traceback (most recent call last):
        ...
    ValueError: no declaration found for <addon_toolkit.declarator.MyLongLivedBaseClass object at 0x...>
    >>> class Foo(MyLongLivedBaseClass):
    ...   pass
    >>> semver.get_declaration(Foo)
    Traceback (most recent call last):
        ...
    ValueError: no declaration found for <class 'addon_toolkit.declarator.Foo'>

    to recognize a subclass of a declarated class, use `get_declaration_for_class` (returns the first declaration found on items in `__mro__`)
    >>> semver.get_declaration_for_class(Foo)
    SemanticVersionDeclaration(major=4, minor=2, patch=9, subj=<class 'addon_toolkit.declarator.MyLongLivedBaseClass'>)

    to also recognize an instance of a class, use `get_declaration_for_class_or_instance`:
    >>> semver.get_declaration_for_class_or_instance(Foo())
    SemanticVersionDeclaration(major=4, minor=2, patch=9, subj=<class 'addon_toolkit.declarator.MyLongLivedBaseClass'>)
    """

    def get_declaration_for_class_or_instance(self, type_or_object: type | object):
        _cls = (
            type_or_object if isinstance(type_or_object, type) else type(type_or_object)
        )
        return self.get_declaration_for_class(_cls)

    def get_declaration_for_class(self, cls: type):
        for _cls in cls.__mro__:
            try:
                return self.get_declaration(_cls)
            except ValueError:  # TODO: more helpful exception
                pass
        raise ValueError(f"no declaration found for {cls}")
