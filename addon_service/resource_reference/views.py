from addon_service.common.permissions import SessionUserCanViewReferencedResource
from addon_service.common.viewsets import RestrictedReadOnlyViewSet
from addon_service.serializers import ResourceReferenceSerializer

from .models import ResourceReference


class ResourceReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = ResourceReference.objects.all()
    serializer_class = ResourceReferenceSerializer
    permission_classes = [SessionUserCanViewReferencedResource]
    allowed_query_params = ["view_only"]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("resource_uri",)
