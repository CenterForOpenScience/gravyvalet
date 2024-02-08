from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import InternalResource
from .serializers import InternalResourceSerializer


class InternalResourceViewSet(ReadOnlyModelViewSet):
    queryset = InternalResource.objects.all()
    serializer_class = InternalResourceSerializer
    # TODO: permissions_classes
