from addon_service.common.permissions import SessionUserIsOwner
from addon_service.common.viewsets import RestrictedReadOnlyViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer
from ..common.uri_filter import URIFilter


class UserReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    permission_classes = [
        SessionUserIsOwner,
    ]
    filter_backends = [URIFilter]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("user_uri",)
