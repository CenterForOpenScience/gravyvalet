from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalCitationService
from .serializers import ExternalCitationServiceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get the list of all available external citation services"
    ),
    get=extend_schema(
        description="Get particular external citation service",
    ),
)
class ExternalCitationServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalCitationService.objects.all().select_related(
        "oauth2_client_config", "oauth1_client_config"
    )
    serializer_class = ExternalCitationServiceSerializer
