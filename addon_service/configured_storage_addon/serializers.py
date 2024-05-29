from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.enum_serializers import EnumNameMultipleChoiceField
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
)
from addon_toolkit import AddonCapabilities


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredStorageAddon)


class ConfiguredStorageAddonSerializer(serializers.HyperlinkedModelSerializer):
    root_folder = serializers.CharField(required=False)
    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    connected_capabilities = EnumNameMultipleChoiceField(enum_cls=AddonCapabilities)
    connected_operation_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    connected_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )
    base_account = ResourceRelatedField(
        queryset=AuthorizedStorageAccount.objects.all(),
        many=False,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource_uri = serializers.CharField(
        required=False, source="resource_uri", write_only=True
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedStorageAccountSerializer"
        ),
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredStorageAddon
        fields = [
            "id",
            "url",
            "root_folder",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
        ]


class WaterButlerConfigurationSerializer(serializers.Serializer):
    """Serialize ConfiguredStorageAccount information required by WaterButler.

    The returned data should share a shape with the existing `serialize_waterbutler_credentials`
    and `serialize_waterbutler_settings` functions used by the OSF-based Addons.
    """

    credentials = serializers.JSONField()
    settings = serializers.JSONField()
