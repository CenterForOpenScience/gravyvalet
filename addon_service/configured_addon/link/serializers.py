from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.configured_addon.serializers import ConfiguredAddonSerializer
from addon_service.external_service.link.models import ExternalLinkService
from addon_service.models import (
    AuthorizedLinkAccount,
    ConfiguredLinkAddon,
)


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredLinkAddon)


class ConfiguredLinkAddonSerializer(ConfiguredAddonSerializer):
    """api serializer for the `ConfiguredLinkAddon` model"""

    root_folder = serializers.CharField(required=False, allow_blank=True)
    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    connected_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )
    base_account = ResourceRelatedField(
        queryset=AuthorizedLinkAccount.objects.all(),
        many=False,
        source="base_account.authorizedlinkaccount",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    external_link_service = ResourceRelatedField(
        many=False,
        read_only=True,
        model=ExternalLinkService,
        source="base_account.external_service.externallinkservice",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedLinkAccountSerializer"
        ),
        "external_link_service": "addon_service.serializers.ExternalLinkServiceSerializer",
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredLinkAddon
        read_only_fields = ["external_link_service"]
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
            "external_link_service",
            "current_user_is_owner",
            "external_service_name",
        ]
