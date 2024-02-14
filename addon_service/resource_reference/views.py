from addon_service.common.permissions import SessionUserIsResourceReferenceOwner
from addon_service.common.viewsets import RetrieveOnlyViewSet
from addon_service.serializers import ResourceReferenceSerializer

from .models import ResourceReference


class ResourceReferenceViewSet(RetrieveOnlyViewSet):
    queryset = ResourceReference.objects.all()
    serializer_class = ResourceReferenceSerializer
    permission_classes = [SessionUserIsResourceReferenceOwner]
