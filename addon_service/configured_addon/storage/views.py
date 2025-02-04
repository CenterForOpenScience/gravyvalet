from http import HTTPMethod

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.waterbutler_compat import WaterButlerConfigSerializer
from addon_service.configured_addon.views import ConfiguredAddonViewSet

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
    def get_wb_credentials(self, request, pk=None):
        addon: ConfiguredStorageAddon = self.get_object()
        token_expiration = (
            addon.base_account.oauth2_token_metadata.access_token_expiration
        )
        if (
            addon.external_service.credentials_format is CredentialsFormats.OAUTH2
            and token_expiration
            and token_expiration < timezone.now()
        ):
            addon.base_account.refresh_oauth_access_token__blocking()
        self.resource_name = "waterbutler-credentials"  # for the jsonapi resource type
        return Response(WaterButlerConfigSerializer(addon).data)
