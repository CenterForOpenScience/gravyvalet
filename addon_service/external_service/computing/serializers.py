from rest_framework_json_api import serializers
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedDataField
from addon_service.external_service.serializers import ExternalServiceSerializer
from addon_service.models import ExternalComputingService


RESOURCE_TYPE = get_resource_type_from_model(ExternalComputingService)


class ExternalComputingServiceSerializer(ExternalServiceSerializer):
    """api serializer for the `ExternalComputing` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    addon_imp = DataclassRelatedDataField(
        dataclass_model=AddonImpModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    class Meta:
        model = ExternalComputingService
        fields = [
            "id",
            "addon_imp",
            "auth_uri",
            "credentials_format",
            "display_name",
            "url",
            "configurable_api_root",
        ]
