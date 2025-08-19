from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.common.permissions import SessionUserIsOwner
from addon_service.common.viewsets import RestrictedReadOnlyViewSet

from .models import UserReference
from .serializers import UserReferenceSerializer


@extend_schema_view(
    list=extend_schema(
        description="Get user reference by user_uri. Even though this is a list method, this endpoint returns only one entity"
    ),
    retrieve=extend_schema(
        description="Get user reference by its pk",
    ),
)
class UserReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = UserReference.objects.all()
    serializer_class = UserReferenceSerializer
    permission_classes = [
        SessionUserIsOwner,
    ]
    allowed_query_params = ["uris"]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("user_uri",)
