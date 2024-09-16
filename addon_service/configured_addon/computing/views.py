from http import HTTPMethod

from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.common.waterbutler_compat import WaterButlerConfigSerializer
from addon_service.configured_addon.views import ConfiguredAddonViewSet

from .models import ConfiguredComputingAddon
from .serializers import ConfiguredComputingAddonSerializer


class ConfiguredComputingAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredComputingAddon.objects.active()
    serializer_class = ConfiguredComputingAddonSerializer

    @action(
        detail=True,
        methods=[HTTPMethod.GET],
        url_name="waterbutler-credentials",
        url_path="waterbutler-credentials",
    )
    def get_wb_credentials(self, request, pk=None):
        addon: ConfiguredComputingAddon = self.get_object()
        self.resource_name = "waterbutler-credentials"  # for the jsonapi resource type
        return Response(WaterButlerConfigSerializer(addon).data)
