from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalRedirectService
from .serializers import ExternalRedirectServiceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get the list of all available external redirect services"
    ),
    get=extend_schema(
        description="Get particular external redirect service",
    ),
)
class ExternalRedirectServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalRedirectService.objects.all()
    serializer_class = ExternalRedirectServiceSerializer
