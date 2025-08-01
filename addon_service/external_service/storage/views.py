from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalStorageService
from .serializers import ExternalStorageServiceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get the list of all available external storage services"
    ),
)
class ExternalStorageServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalStorageService.objects.all().select_related(
        "oauth2_client_config"
    )
    serializer_class = ExternalStorageServiceSerializer
