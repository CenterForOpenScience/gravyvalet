from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.enums.serializers import EnumNameMultipleChoiceField
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
    ResourceReference,
)
from addon_toolkit import AddonCapabilities


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredStorageAddon)


class AuthorizedResourceField(ResourceRelatedField):
    def to_internal_value(self, data):
        resource_reference, _ = ResourceReference.objects.get_or_create(
            resource_uri=data["resource_uri"]
        )
        return resource_reference


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
    authorized_resource = AuthorizedResourceField(
        queryset=ResourceReference.objects.all(),
        many=False,
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
            "url",
            "root_folder",
            "base_account",
            "authorized_resource",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
        ]
