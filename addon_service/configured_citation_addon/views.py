from ..abstract.configured_addon.views import ConfiguredAddonViewSet
from .models import ConfiguredCitationAddon
from .serializers import ConfiguredCitationAddonSerializer


class ConfiguredStorageAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredCitationAddon.objects.active()
    serializer_class = ConfiguredCitationAddonSerializer
