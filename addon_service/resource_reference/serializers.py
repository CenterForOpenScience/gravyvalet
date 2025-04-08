from rest_framework_json_api import serializers
from rest_framework_json_api.relations import HyperlinkedRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common import view_names
from addon_service.configured_addon.citation.models import ConfiguredCitationAddon
from addon_service.configured_addon.computing.models import ConfiguredComputingAddon
from addon_service.models import (
    ConfiguredStorageAddon,
    ResourceReference,
)


RESOURCE_TYPE = get_resource_type_from_model(ResourceReference)


class ResourceReferenceSerializer(serializers.HyperlinkedModelSerializer):
    """api serializer for the `ResourceReference` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    configured_storage_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredStorageAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_citation_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredCitationAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_link_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredCitationAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_computing_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredComputingAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "configured_storage_addons": (
            "addon_service.serializers.ConfiguredStorageAddonSerializer"
        ),
        "configured_citation_addons": (
            "addon_service.serializers.ConfiguredCitationAddonSerializer"
        ),
        "configured_link_addons": (
            "addon_service.serializers.ConfiguredComputingAddonSerializer"
        ),
        "configured_computing_addons": (
            "addon_service.serializers.ConfiguredComputingAddonSerializer"
        ),
    }

    class Meta:
        model = ResourceReference
        fields = [
            "id",
            "url",
            "resource_uri",
            "configured_storage_addons",
            "configured_link_addons",
            "configured_citation_addons",
            "configured_computing_addons",
        ]
