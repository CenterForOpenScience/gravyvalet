from rest_framework_json_api.views import ReadOnlyModelViewSet

from .models import InternalUser
from .serializers import InternalUserSerializer


class InternalUserViewSet(ReadOnlyModelViewSet):
    queryset = InternalUser.objects.all()
    serializer_class = InternalUserSerializer
    # TODO: permissions_classes
