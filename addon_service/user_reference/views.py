from addon_service.common.permissions import SessionUserIsUserReference
from addon_service.common.viewsets import RetrieveOnlyViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer


class UserReferenceViewSet(RetrieveOnlyViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    permission_classes = [
        SessionUserIsUserReference,
    ]
