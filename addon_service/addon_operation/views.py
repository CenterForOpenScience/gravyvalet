from rest_framework.permissions import AllowAny

from addon_service.common.viewsets import DataclassViewset

from .serializers import AddonOperationSerializer


class AddonOperationViewSet(DataclassViewset):
    serializer_class = AddonOperationSerializer
    permission_classes = [AllowAny]
