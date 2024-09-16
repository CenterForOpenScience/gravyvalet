from rest_framework_json_api import serializers

from addon_service.configured_addon.citation.serializers import (
    ConfiguredCitationAddonSerializer,
)
from addon_service.configured_addon.computing.serializers import (
    ConfiguredComputingAddonSerializer,
)
from addon_service.configured_addon.models import ConfiguredAddon
from addon_service.configured_addon.storage.serializers import (
    ConfiguredStorageAddonSerializer,
)


class ConfiguredAddonPolymorphicSerializer(serializers.PolymorphicModelSerializer):
    polymorphic_serializers = [
        ConfiguredCitationAddonSerializer,
        ConfiguredComputingAddonSerializer,
        ConfiguredStorageAddonSerializer,
    ]

    class Meta:
        model = ConfiguredAddon
