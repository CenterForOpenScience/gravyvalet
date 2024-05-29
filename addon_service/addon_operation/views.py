from rest_framework.permissions import AllowAny

from addon_service.common.viewsets import StaticDataclassViewset

from .serializers import AddonOperationSerializer


class AddonOperationViewSet(StaticDataclassViewset):
    serializer_class = AddonOperationSerializer
    permission_classes = [AllowAny]
