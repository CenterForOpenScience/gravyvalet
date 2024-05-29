from addon_service.common.permissions import SessionUserIsOwner
from addon_service.common.viewsets import RestrictedReadOnlyViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer


class UserReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    permission_classes = [
        SessionUserIsOwner,
    ]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("user_uri",)
