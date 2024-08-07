from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.abstract.configured_addon.serializers import (
    ConfiguredAddonSerializer,
)
from addon_service.models import ConfiguredCitationAddon


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredCitationAddon)


class ConfiguredCitationAddonSerializer(ConfiguredAddonSerializer):
    pass
