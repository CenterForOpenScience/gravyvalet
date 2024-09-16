from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.authorized_account.computing.models import AuthorizedComputingAccount
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.configured_addon.computing.models import ConfiguredComputingAddon
from addon_service.configured_addon.serializers import ConfiguredAddonSerializer
from addon_service.external_service.computing.models import ExternalComputingService


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredComputingAddon)


class ConfiguredComputingAddonSerializer(ConfiguredAddonSerializer):
    """api serializer for the `ConfiguredComputingAddon` model"""

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
        queryset=AuthorizedComputingAccount.objects.all(),
        many=False,
        source="base_account.authorizedcomputingaccount",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    external_computing_service = ResourceRelatedField(
        many=False,
        read_only=True,
        model=ExternalComputingService,
        source="base_account.external_service.externalcomputingservice",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedComputingAccountSerializer"
        ),
        "external_computing_service": (
            "addon_service.serializers.ExternalComputingServiceSerializer"
        ),
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredComputingAddon
        fields = [
            "id",
            "url",
            "display_name",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
            "external_service_name",
            "external_computing_service",
        ]
