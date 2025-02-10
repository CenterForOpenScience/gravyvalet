from http import HTTPMethod

from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.waterbutler_compat import WaterButlerConfigSerializer
from addon_service.configured_addon.views import ConfiguredAddonViewSet
from app.settings import ALLOWED_RESOURCE_URI_PREFIXES

from .models import ConfiguredStorageAddon
from .serializers import ConfiguredStorageAddonSerializer


class ConfiguredStorageAddonViewSet(ConfiguredAddonViewSet):
    queryset = ConfiguredStorageAddon.objects.active().select_related(
        "base_account__authorizedstorageaccount",
        "base_account__account_owner",
        "base_account__external_service__externalstorageservice",
        "authorized_resource",
    )
    serializer_class = ConfiguredStorageAddonSerializer

    @action(
        detail=True,
        methods=[HTTPMethod.GET],
        url_name="waterbutler-credentials",
        url_path="waterbutler-credentials",
    )
    def get_wb_credentials(self, request, pk: str = None):
        if ":" in pk:
            guid, external_service_name = pk.split(":", maxsplit=1)
            addon: ConfiguredStorageAddon = ConfiguredStorageAddon.objects.get(
                base_account__external_service__wb_key=external_service_name,
                authorized_resource__resource_uri__in=[
                    f"{prefix}/{guid}" for prefix in ALLOWED_RESOURCE_URI_PREFIXES
                ],
            )
        else:
            addon = self.get_object()
        if addon.external_service.credentials_format is CredentialsFormats.OAUTH2:
            addon.base_account.refresh_oauth_access_token__blocking()
        self.resource_name = "waterbutler-credentials"  # for the jsonapi resource type
        return Response(WaterButlerConfigSerializer(addon).data)
