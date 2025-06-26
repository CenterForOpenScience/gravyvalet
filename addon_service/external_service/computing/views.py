from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalComputingService
from .serializers import ExternalComputingServiceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get the list of all available external computing services"
    ),
    get=extend_schema(
        description="Get particular external computing service",
    ),
)
class ExternalComputingServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalComputingService.objects.all().select_related(
        "oauth2_client_config"
    )
    serializer_class = ExternalComputingServiceSerializer
