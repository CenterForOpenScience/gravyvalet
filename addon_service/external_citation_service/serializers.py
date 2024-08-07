from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.abstract.external_storage.serializers import (
    ExternalServiceSerializer,
)
from addon_service.models import ExternalCitationService


RESOURCE_TYPE = get_resource_type_from_model(ExternalCitationService)


class ExternalCitationServiceSerializer(ExternalServiceSerializer):
    pass
