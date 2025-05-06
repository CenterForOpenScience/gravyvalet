import enum

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from addon_service.common.enum_utils import combine_flags


__all__ = ("GravyvaletModelAdmin",)


class EnumNameMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(self, *args, enum_cls=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.enum_cls = enum_cls

    def to_python(self, value):
        if not value:
            return None
        elif not isinstance(value, (list, tuple)):
            raise ValidationError(
                self.error_messages["invalid_list"], code="invalid_list"
            )
        return combine_flags([int(item) for item in value])

    def prepare_value(self, value):
        value = super().prepare_value(value)
        if type(value) is list:
            return [
                item.value
                for item in self.enum_cls(combine_flags([int(item) for item in value]))
            ]
        elif isinstance(value, int):
            return [item.value for item in self.enum_cls(value)]
        else:
            return []

    def validate(self, value) -> None:
        return True

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        return data != initial


class GravyvaletModelAdmin(admin.ModelAdmin):
    enum_choice_fields: dict[str, type[enum.Enum]] | None = None
    enum_multiple_choice_fields: dict[str, type[enum.Enum]] | None = None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if self.enum_choice_fields and db_field.name in self.enum_choice_fields:
            _enum = self.enum_choice_fields[db_field.name]
            return forms.ChoiceField(
                label=db_field.verbose_name,
                choices=[
                    (None, ""),
                    *self.iter_enum_members(_enum),
                ],
            )
        if (
            self.enum_multiple_choice_fields
            and db_field.name in self.enum_multiple_choice_fields
        ):
            _enum = self.enum_multiple_choice_fields[db_field.name]
            return EnumNameMultipleChoiceField(
                choices=self.iter_enum_members(_enum),
                widget=forms.CheckboxSelectMultiple,
                enum_cls=_enum,
            )

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def iter_enum_members(self, _enum):
        if hasattr(_enum, "__members__"):
            iterator = _enum.__members__.values()
        else:
            iterator = _enum

        return [(_member.value, _member.name) for _member in iterator]
