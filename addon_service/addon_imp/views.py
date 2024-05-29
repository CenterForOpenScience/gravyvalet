from rest_framework.permissions import AllowAny

from addon_service.common.viewsets import StaticDataclassViewset

from .serializers import AddonImpSerializer


class AddonImpViewSet(StaticDataclassViewset):
    serializer_class = AddonImpSerializer
    permission_classes = [AllowAny]
