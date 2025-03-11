from http import HTTPMethod

from django.http import Http404
from rest_framework.decorators import action
from rest_framework.response import Response

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.permissions import IsValidHMACSignedRequest
from addon_service.common.waterbutler_compat import WaterButlerConfigSerializer
from addon_service.configured_addon.views import ConfiguredAddonViewSet
from app.settings import ALLOWED_RESOURCE_URI_PREFIXES

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

    def get_object(self):
        pk = self.kwargs["pk"]
        if ":" in pk:
            # Make sure only a valid HMAC request can query this endpoint using
            # pk in "<guid>:<addon_name>" format
            IsValidHMACSignedRequest().has_permission(self.request, self)
            guid, external_service_name = pk.split(":", maxsplit=1)
            try:
                addon: ConfiguredLinkAddon = ConfiguredLinkAddon.objects.get(
                    base_account__external_service__wb_key=external_service_name,
                    authorized_resource__resource_uri__in=[
                        f"{prefix}/{guid}" for prefix in ALLOWED_RESOURCE_URI_PREFIXES
                    ],
                )
            except ConfiguredLinkAddon.DoesNotExist:
                raise Http404
            self.check_object_permissions(self.request, addon)
            return addon
        else:
            return super().get_object()

    @action(
        detail=True,
        methods=[HTTPMethod.GET],
        url_name="waterbutler-credentials",
        url_path="waterbutler-credentials",
    )
    def get_wb_credentials(self, request, pk: str = None):
        addon = self.get_object()
        if addon.external_service.credentials_format is CredentialsFormats.OAUTH2:
            addon.base_account.refresh_oauth_access_token__blocking()
        self.resource_name = "waterbutler-credentials"  # for the jsonapi resource type
        return Response(WaterButlerConfigSerializer(addon).data)
