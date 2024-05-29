from addon_service.common.permissions import (
    IsAuthenticated,
    SessionUserIsOwner,
    SessionUserMayAccessInvocation,
)
from addon_service.common.viewsets import RetrieveWriteViewSet

from .models import AddonOperationInvocation
from .serializers import AddonOperationInvocationSerializer


class AddonOperationInvocationViewSet(RetrieveWriteViewSet):
    queryset = AddonOperationInvocation.objects.all()
    serializer_class = AddonOperationInvocationSerializer

    def get_permissions(self):
        match self.action:
            case "retrieve" | "retrieve_related":
                return [IsAuthenticated(), SessionUserMayAccessInvocation()]
            case "partial_update" | "update" | "destroy":
                return [IsAuthenticated(), SessionUserIsOwner()]
            case "create":
                return [IsAuthenticated()]  # additional checks in serializer
            case None:
                return super().get_permissions()
            case _:
                raise NotImplementedError(
                    f"no permission implemented for action '{self.action}'"
                )
