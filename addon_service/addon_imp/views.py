from rest_framework.permissions import AllowAny

from addon_service.common.viewsets import DataclassViewset

from .serializers import AddonImpSerializer


class AddonImpViewSet(DataclassViewset):
    serializer_class = AddonImpSerializer
    permission_classes = [AllowAny]
