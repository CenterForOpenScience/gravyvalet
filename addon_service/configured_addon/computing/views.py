from http import HTTPMethod

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.common.waterbutler_compat import WaterButlerConfigSerializer
from addon_service.configured_addon.views import ConfiguredAddonViewSet

from .models import ConfiguredComputingAddon
from .serializers import ConfiguredComputingAddonSerializer


@extend_schema_view(
    create=extend_schema(
        description="Create new configured computing addon for given authorized computing account, linking it to desired project.\n "
        "To configure it properly, you must specify `root_folder` on the provider's side.\n "
        "Note that everything under this folder is going to be accessible to everyone who has access to this project"
    ),
    get=extend_schema(
        description="Get configured computing addon by its pk. "
        "\nIf you want to fetch all configured computing addons, you should do so through resource_reference related view",
    ),
    get_wb_credentials=extend_schema(exclude=True),
)
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
