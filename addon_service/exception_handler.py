from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError
from rest_framework.response import Response
from rest_framework_json_api import serializers
from rest_framework_json_api.exceptions import (
    exception_handler as drfja_exception_handler,
)


def api_exception_handler(exception: Exception, context: dict) -> Response | None:
    """custom api exception handler

    as defined by django-rest-framework:
    https://www.django-rest-framework.org/api-guide/exceptions/#custom-exception-handling

    return a 400 response for django model validation errors, same as
    django-rest-framework serializer validation errors

    OHNO: does not translate to serializer field names -- may be a problem if model field names differ
    """
    _api_exception = (
        RestFrameworkValidationError(detail=serializers.as_serializer_error(exception))
        if isinstance(exception, DjangoValidationError)
        else exception
    )
    return drfja_exception_handler(_api_exception, context)
