from rest_framework_json_api import serializers
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common import view_names
from addon_service.common.enum_serializers import EnumNameMultipleChoiceField
from addon_service.common.serializer_fields import DataclassRelatedDataField
from addon_service.external_service.serializers import ExternalServiceSerializer
from addon_service.external_service.link.models import LinkSupportedFeatures
from addon_service.models import ExternalLinkService


RESOURCE_TYPE = get_resource_type_from_model(ExternalLinkService)


class ExternalLinkServiceSerializer(ExternalServiceSerializer):
    """api serializer for the `ExternalService` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )

    addon_imp = DataclassRelatedDataField(
        dataclass_model=AddonImpModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    supported_features = EnumNameMultipleChoiceField(
        enum_cls=LinkSupportedFeatures, read_only=True
    )

    class Meta:
        model = ExternalLinkService
        fields = [
            "id",
            "addon_imp",
            "auth_uri",
            "credentials_format",
            "max_concurrent_downloads",
            "max_upload_mb",
            "display_name",
            "url",
            "wb_key",
            "external_service_name",
            "configurable_api_root",
            "supported_features",
            "icon_url",
            "api_base_url_options",
        ]
