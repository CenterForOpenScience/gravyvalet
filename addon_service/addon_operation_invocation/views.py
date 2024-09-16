from rest_framework.response import Response

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

from ..authorized_account.citation.serializers import (
    AuthorizedCitationAccountSerializer,
)
from ..authorized_account.computing.serializers import (
    AuthorizedComputingAccountSerializer,
)
from ..authorized_account.models import AuthorizedAccount
from ..authorized_account.storage.serializers import AuthorizedStorageAccountSerializer
from ..configured_addon.citation.serializers import ConfiguredCitationAddonSerializer
from ..configured_addon.computing.serializers import ConfiguredComputingAddonSerializer
from ..configured_addon.models import ConfiguredAddon
from ..configured_addon.storage.serializers import ConfiguredStorageAddonSerializer
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
                return [IsAuthenticated(), SessionUserMayPerformInvocation()]
            case None:
                return super().get_permissions()
            case _:
                raise NotImplementedError(
                    f"no permission implemented for action '{self.action}'"
                )

    def retrieve_related(self, request, *args, **kwargs):
        instance = self.get_related_instance()
        if isinstance(instance, AuthorizedAccount):
            if hasattr(instance, "authorizedstorageaccount"):
                serializer = AuthorizedStorageAccountSerializer(
                    instance, context={"request": request}
                )
            elif hasattr(instance, "authorizedcitationaccount"):
                serializer = AuthorizedCitationAccountSerializer(
                    instance, context={"request": request}
                )
            elif hasattr(instance, "authorizedcomputingaccount"):
                serializer = AuthorizedComputingAccountSerializer(
                    instance, context={"request": request}
                )
            else:
                raise ValueError("unknown authorized account type")
        elif isinstance(instance, ConfiguredAddon):
            if hasattr(instance, "configuredstorageaddon"):
                serializer = ConfiguredStorageAddonSerializer(
                    instance, context={"request": request}
                )
            elif hasattr(instance, "configuredcitationaddon"):
                serializer = ConfiguredCitationAddonSerializer(
                    instance, context={"request": request}
                )
            elif hasattr(instance, "configuredcomputingaddon"):
                serializer = ConfiguredComputingAddonSerializer(
                    instance, context={"request": request}
                )
            else:
                raise ValueError("unknown configured addon type")
        else:
            serializer = self.get_related_serializer(instance)
        return Response(serializer.data)

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
