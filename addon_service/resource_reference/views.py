from addon_service.common.permissions import SessionUserCanViewReferencedResource
from addon_service.common.viewsets import RestrictedReadOnlyViewSet
from addon_service.serializers import ResourceReferenceSerializer

from ..common.view_only_filter import ViewOnlyFilter
from .models import ResourceReference


class ResourceReferenceViewSet(RestrictedReadOnlyViewSet):
    queryset = ResourceReference.objects.all()
    serializer_class = ResourceReferenceSerializer
    permission_classes = [SessionUserCanViewReferencedResource]
    filter_backends = [ViewOnlyFilter]
    # Satisfies requirements of `RestrictedReadOnlyViewSet.list`
    required_list_filter_fields = ("resource_uri",)
