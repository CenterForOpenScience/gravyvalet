from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.abstract.configured_addon.serializers import (
    ConfiguredAddonSerializer,
)
from addon_service.addon_operation.models import AddonOperationModel
from addon_service.authorized_citation_account.models import AuthorizedCitationAccount
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.configured_citation_addon.models import ConfiguredCitationAddon


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredCitationAddon)


class ConfiguredCitationAddonSerializer(ConfiguredAddonSerializer):
    """api serializer for the `ConfiguredCitationAddon` model"""

    root_folder = serializers.CharField(required=False, allow_blank=True)
    external_service_name = serializers.CharField(read_only=True)
    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    connected_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )
    base_account = ResourceRelatedField(
        queryset=AuthorizedCitationAccount.objects.all(),
        many=False,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedCitationAccountSerializer"
        ),
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredCitationAddon
        fields = [
            "id",
            "url",
            "display_name",
            "root_folder",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
            "external_service_name",
        ]
