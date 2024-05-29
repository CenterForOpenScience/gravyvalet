import enum

from rest_framework_json_api import serializers

from .enum_utils import combine_flags


ENUM_BASE_CLASSES = [
    enum.Enum,
    enum.IntEnum,
    enum.ReprEnum,
    enum.StrEnum,
    enum.Flag,
    enum.IntFlag,
]


class _BaseEnumNameChoiceField(serializers.ChoiceField):
    SUPPORTED_ENUM_BASE_CLASS = enum.Enum
    enum_cls: type[enum.Enum]

    def __init__(self, enum_cls: type[enum.Enum], **kwargs):
        assert issubclass(enum_cls, self.SUPPORTED_ENUM_BASE_CLASS)
        assert not any(enum_cls is base_class for base_class in ENUM_BASE_CLASSES)
        self.enum_cls = enum_cls
        super().__init__(
            **kwargs,
            choices=(_member.name for _member in enum_cls),
        )


class EnumNameChoiceField(_BaseEnumNameChoiceField):
    """serializer field allowing member names (as strings) from a given enum

    note: the "internal value" is the enum member (not the member `value`)
    so if you use this for updates, make sure your model supports this translation
    """

    def to_internal_value(self, data) -> enum.Enum:
        _name = super().to_internal_value(data)
        return self.enum_cls[_name]

    def to_representation(self, value: enum.Enum):
        return super().to_representation(value).name


class EnumNameMultipleChoiceField(
    _BaseEnumNameChoiceField, serializers.MultipleChoiceField
):
    """serializer field allowing a set of member names (as a list of strings) from a given enum

    note: the "internal value" is a combined Flag member, not the resulting int value
    so if you use this for updates, make sure your model supports this translation
    """

    SUPPORTED_ENUM_BASE_CLASS = enum.Flag

    def to_internal_value(self, data) -> enum.Flag:
        _names: set = super().to_internal_value(data)
        return combine_flags([self.enum_cls[_name] for _name in _names])

    def to_representation(self, value):
        _member_list = super().to_representation(value)
        return [_member.name for _member in _member_list]
