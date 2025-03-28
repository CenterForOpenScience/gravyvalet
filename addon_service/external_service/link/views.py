from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalLinkService
from .serializers import ExternalLinkServiceSerializer


class ExternalLinkServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalLinkService.objects.all().select_related("oauth2_client_config")
    serializer_class = ExternalLinkServiceSerializer
