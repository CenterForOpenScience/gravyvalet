from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import ResourceReference
from .serializers import ResourceReferenceSerializer


class ResourceReferenceViewSet(ReadOnlyModelViewSet):
    queryset = ResourceReference.objects.all()
    serializer_class = ResourceReferenceSerializer
    # TODO: permissions_classes
