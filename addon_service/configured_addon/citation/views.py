from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.configured_addon.views import ConfiguredAddonViewSet

from .models import ConfiguredCitationAddon
from .serializers import ConfiguredCitationAddonSerializer


@extend_schema_view(
    create=extend_schema(
        description="Create new configured citation addon for given authorized citation account, linking it to desired project.\n "
        "To configure it properly, you must specify `root_folder` on the provider's side.\n "
        "Note that everything under this folder is going to be accessible to everyone who has access to this project"
    ),
    get=extend_schema(
        description="Get configured citation addon by it's pk. "
        "\nIf you want to fetch all configured citation addons, you should do so through resource_reference related view",
    ),
)
class ConfiguredCitationAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredCitationAddon.objects.active()
    serializer_class = ConfiguredCitationAddonSerializer
