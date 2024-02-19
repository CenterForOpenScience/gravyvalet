from addon_service.common.permissions import SessionUserIsOwner
from addon_service.common.viewsets import RetrieveOnlyViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer


class UserReferenceViewSet(RetrieveOnlyViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    permission_classes = [
        SessionUserIsOwner,
    ]
