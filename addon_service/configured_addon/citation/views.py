from addon_service.configured_addon.views import ConfiguredAddonViewSet

from .models import ConfiguredCitationAddon
from .serializers import ConfiguredCitationAddonSerializer


class ConfiguredCitationAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredCitationAddon.objects.active()
    serializer_class = ConfiguredCitationAddonSerializer
