from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer


class UserReferenceViewSet(ReadOnlyModelViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    # TODO: permissions_classes
