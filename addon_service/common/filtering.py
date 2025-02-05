from django.http.request import QueryDict
from rest_framework import (
    fields,
    filters,
    serializers,
)

from .jsonapi import (
    JSONAPIQueryParam,
    group_query_params_by_family,
)


class AddonServiceFilteringBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_expressions = extract_filter_expressions(
            request.query_params, view.get_serializer()
        )
        return queryset.filter(**filter_expressions)


class RestrictedListEndpointFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        required_filters = set(view.required_list_filter_fields)
        filter_expressions = extract_filter_expressions(
            request.query_params, view.get_serializer()
        )
        missing_filters = required_filters - filter_expressions.keys()
        if missing_filters:
            raise serializers.ValidationError(
                f"Request was missing the following required filters for this endpoint: {missing_filters}"
            )
        return queryset.filter(**filter_expressions)


def extract_filter_expressions(
    query_dict: QueryDict, serializer: serializers.Serializer
) -> dict[str, str]:
    """Extract the "filter" family of expressions from the query dict and format them for use.

    Since no formal JSON:API scheme exists for complex filter operations, we have settled on the following norm:
    Filter params can have either one or two arguments.
    The first argument MUST be a field on the serialized output of the endpoint
    The second argument is an OPTIONAL comparison operator (i.e. `icontains`, `lte`, etc.)

    >>> from addon_service.models import UserReference
    >>> class DemoSerializer(serializers.Serializer):
    ...   user_uri = serializers.CharField()
    ...   renamed_id = serializers.IntegerField(source="id")
    ...   class Meta:
    ...     model = UserReference

    >>> query_dict = QueryDict("filter[user_uri]=value&filter[renamed_id][lt]=4&notafilter=zzz")
    >>> extract_filter_expressions(query_dict, DemoSerializer())
    {'user_uri': 'value', 'id__lt': 4}

    >>> query_dict = QueryDict("filter")
    >>> extract_filter_expressions(query_dict, DemoSerializer())
    Traceback (most recent call last):
    rest_framework.exceptions.ValidationError...

    >>> query_dict = QueryDict("filter[non_field]")
    >>> extract_filter_expressions(query_dict, DemoSerializer())
    Traceback (most recent call last):
    rest_framework.exceptions.ValidationError...

    >>> query_dict = QueryDict("filter[user_uri][isnull][extra]")
    >>> extract_filter_expressions(query_dict, DemoSerializer())
    Traceback (most recent call last):
    rest_framework.exceptions.ValidationError...

    >>> query_dict = QueryDict("filter[user_uri][invalid]")
    >>> extract_filter_expressions(query_dict, DemoSerializer())
    Traceback (most recent call last):
    rest_framework.exceptions.ValidationError...
    """
    filter_params = group_query_params_by_family(query_dict.lists()).get("filter", [])
    return dict([_format_filter_param(param, serializer) for param in filter_params])


def _format_filter_param(
    query_param: JSONAPIQueryParam, serializer: serializers.Serializer
) -> tuple[str, str]:
    """Parse and format the query args into a kwarg key suitable for Django filtering."""
    try:
        field = serializer.fields[query_param.args[0]]
    except (IndexError, KeyError):
        raise serializers.ValidationError(
            "Filter query parameters must specify a field to filter on"
        )

    match len(query_param.args):
        case 1:
            operation = None
        case 2:
            operation = query_param.args[1]
        case _:
            raise serializers.ValidationError(
                "Filter query parameters only accept one field and one (optional) comparison operator"
            )
    if operation:
        _validate_operation(serializer, field, operation)
    filter_name = field.source if operation is None else f"{field.source}__{operation}"
    filter_value = field.to_internal_value(query_param.value)
    return (filter_name, filter_value)


def _validate_operation(
    serializer: serializers.Serializer, field: fields.Field, operation_string: str
) -> bool:
    if not hasattr(serializer, "Meta"):
        return True
    model = serializer.Meta.model
    if operation_string not in model._meta.get_field(field.source).get_lookups():
        raise serializers.ValidationError(
            f"{operation_string} is not a valid comparison operation for field {field.field_name}"
        )
    return True
