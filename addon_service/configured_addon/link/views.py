from http import HTTPMethod

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.configured_addon.views import ConfiguredAddonViewSet
from app.settings import ALLOWED_RESOURCE_URI_PREFIXES

from .models import ConfiguredLinkAddon
from .serializers import (
    ConfiguredLinkAddonSerializer,
    VerifiedLinkSerializer,
)


@extend_schema_view(
    create=extend_schema(
        description="Create new configured link addon for given authorized link account, linking it to desired project.\n "
        "To configure it properly, you must specify `root_folder` on the provider's side.\n "
        "Note that everything under this folder is going to be accessible to everyone who has access to this project"
    ),
    get=extend_schema(
        description="Get configured link addon by it's pk. "
        "\nIf you want to fetch all configured link addons, you should do so through resource_reference related view",
    ),
)
class ConfiguredLinkAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredLinkAddon.objects.active().select_related(
        "base_account__authorizedlinkaccount",
        "base_account__account_owner",
        "base_account__external_service__externallinkservice",
        "authorized_resource",
    )
    serializer_class = ConfiguredLinkAddonSerializer

    @action(
        detail=True,
        methods=[HTTPMethod.GET],
        url_name="verified-links",
        url_path="verified-links",
    )
    def get_verified_links(self, request, pk=None):
        addons: ConfiguredLinkAddon = ConfiguredLinkAddon.objects.filter(
            authorized_resource__resource_uri__in=[
                f"{prefix}/{pk}" for prefix in ALLOWED_RESOURCE_URI_PREFIXES
            ],
        ).select_related("base_account__external_service")
        self.resource_name = "verified-link"

        return Response(VerifiedLinkSerializer(addons, many=True).data)
