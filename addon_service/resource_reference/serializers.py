from rest_framework_json_api import serializers
from rest_framework_json_api.relations import HyperlinkedRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.models import (
    ConfiguredStorageAddon,
    ResourceReference,
)


RESOURCE_NAME = get_resource_type_from_model(ResourceReference)


class ResourceReferenceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=f"{RESOURCE_NAME}-detail")
    configured_storage_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredStorageAddon.objects.active.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    included_serializers = {
        "configured_storage_addons": (
            "addon_service.serializers.ConfiguredStorageAddonSerializer"
        ),
    }

    class Meta:
        model = ResourceReference
        fields = [
            "url",
            "resource_uri",
            "configured_storage_addons",
        ]
