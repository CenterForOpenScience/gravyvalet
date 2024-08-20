import enum

from django import forms
from django.contrib import admin


__all__ = ("GravyvaletModelAdmin",)


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
                    *(
                        (_member.value, _member.name)
                        for _member in _enum.__members__.values()
                    ),
                ],
            )
        if (
            self.enum_multiple_choice_fields
            and db_field.name in self.enum_multiple_choice_fields
        ):
            _enum = self.enum_multiple_choice_fields[db_field.name]
            return forms.TypedMultipleChoiceField(
                choices=[
                    (None, ""),
                    *(
                        (_member.value, _member.name)
                        for _member in _enum.__members__.values()
                    ),
                ],
                coerce=int,
                widget=forms.CheckboxSelectMultiple,
            )

        return super().formfield_for_dbfield(db_field, request, **kwargs)
