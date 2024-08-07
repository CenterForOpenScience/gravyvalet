from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ExternalCitationService
from .serializers import ExternalCitationServiceSerializer


class ExternalStorageServiceViewSet(ReadOnlyModelViewSet):
    queryset = ExternalCitationService.objects.all()
    serializer_class = ExternalCitationServiceSerializer
