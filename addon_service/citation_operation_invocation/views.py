from addon_service.common.permissions import (
    IsAuthenticated,
    SessionUserIsOwner,
    SessionUserMayAccessInvocation,
    SessionUserMayPerformInvocation,
)
from addon_service.common.viewsets import RetrieveWriteViewSet
from addon_service.tasks.invocation import (
    perform_invocation__blocking,
    perform_invocation__celery,
)
from addon_toolkit import AddonOperationType

from .models import CitationOperationInvocation
from .serializers import AddonOperationInvocationSerializer


class CitationOperationInvocationViewSet(RetrieveWriteViewSet):
    queryset = CitationOperationInvocation.objects.all()
    serializer_class = AddonOperationInvocationSerializer

    def get_permissions(self):
        match self.action:
            case "retrieve" | "retrieve_related":
                return [IsAuthenticated(), SessionUserMayAccessInvocation()]
            case "partial_update" | "update" | "destroy":
                return [IsAuthenticated(), SessionUserIsOwner()]
            case "create":
                return [IsAuthenticated(), SessionUserMayPerformInvocation()]
            case None:
                return super().get_permissions()
            case _:
                raise NotImplementedError(
                    f"no permission implemented for action '{self.action}'"
                )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # after creating the AddonOperationInvocation, look into invoking it
        _invocation = serializer.instance
        _operation_type = _invocation.operation.operation_type
        match _operation_type:
            case AddonOperationType.REDIRECT | AddonOperationType.IMMEDIATE:
                perform_invocation__blocking(_invocation)
            case AddonOperationType.EVENTUAL:
                perform_invocation__celery.delay(_invocation.pk)
            case _:
                raise ValueError(f"unknown operation type: {_operation_type}")
