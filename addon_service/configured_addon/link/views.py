from addon_service.configured_addon.views import ConfiguredAddonViewSet

from .models import ConfiguredLinkAddon
from .serializers import ConfiguredLinkAddonSerializer


class ConfiguredLinkAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredLinkAddon.objects.active().select_related(
        "base_account__authorizedlinkaccount",
        "base_account__account_owner",
        "base_account__external_service__externallinkservice",
        "authorized_resource",
    )
    serializer_class = ConfiguredLinkAddonSerializer
