from rest_framework_json_api import serializers
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common import view_names

from addon_service.external_service.serializers import ExternalServiceSerializer

from .models import ExternalRedirectService


RESOURCE_TYPE = get_resource_type_from_model(ExternalRedirectService)


class ExternalRedirectServiceSerializer(ExternalServiceSerializer):
    """api serializer for the `ExternalRedirectService` model"""

    redirect_url = serializers.CharField(
        read_only=True,
    )

    class Meta:
        model = ExternalRedirectService
        fields = [
            "id",
            "addon_imp",
            "auth_uri",
            "credentials_format",
            "display_name",
            "url",
            "wb_key",
            "external_service_name",
            "configurable_api_root",
            "icon_url",
            "api_base_url_options",
            "redirect_url",
        ]
