from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.common.permissions import SessionUserCanViewReferencedResource
from addon_service.common.viewsets import RestrictedReadOnlyViewSet
from addon_service.serializers import ResourceReferenceSerializer

from .models import ResourceReference


@extend_schema_view(
    list=extend_schema(
        description="Get resource reference by resource_uri. Even through this is a list method, this endpoint returns only one entity"
    ),
    retrieve=extend_schema(
        description="Get resource reference by it's pk",
    ),
)
class ResourceReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = ResourceReference.objects.all()
    serializer_class = ResourceReferenceSerializer
    permission_classes = [SessionUserCanViewReferencedResource]
    allowed_query_params = ["view_only"]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("resource_uri",)
