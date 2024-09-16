from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalComputingService
from .serializers import ExternalComputingServiceSerializer


class ExternalComputingServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalComputingService.objects.all()
    serializer_class = ExternalComputingServiceSerializer
