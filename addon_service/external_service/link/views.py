from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalLinkService
from .serializers import ExternalLinkServiceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get the list of all available external link services"
    ),
    get=extend_schema(
        description="Get particular external link service",
    ),
)
class ExternalLinkServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalLinkService.objects.all().select_related("oauth2_client_config")
    serializer_class = ExternalLinkServiceSerializer
