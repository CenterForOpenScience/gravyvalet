from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework.response import Response

from addon_service.common.permissions import (
    IsAuthenticated,
    SessionUserMayAccessInvocation,
    SessionUserMayPerformInvocation,
)
from addon_service.common.viewsets import RetrieveCreateViewSet
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
from ..authorized_account.link.serializers import AuthorizedLinkAccountSerializer
from ..authorized_account.models import AuthorizedAccount
from ..authorized_account.storage.serializers import AuthorizedStorageAccountSerializer
from ..configured_addon.citation.serializers import ConfiguredCitationAddonSerializer
from ..configured_addon.computing.serializers import ConfiguredComputingAddonSerializer
from ..configured_addon.link.serializers import ConfiguredLinkAddonSerializer
from ..configured_addon.models import ConfiguredAddon
from ..configured_addon.storage.serializers import ConfiguredStorageAddonSerializer
from .models import AddonOperationInvocation
from .serializers import AddonOperationInvocationSerializer


@extend_schema_view(
    create=extend_schema(
        description="Perform some action using external service, for instance list files on storage provider. "
        "In order to perform such action you need to include configured_addon relationship"
    ),
    retrieve=extend_schema(
        description="Get singular instance of addon operation invocation by it's pk. May be useful to view action log",
    ),
)
class AddonOperationInvocationViewSet(RetrieveCreateViewSet):
    queryset = AddonOperationInvocation.objects.all()
    serializer_class = AddonOperationInvocationSerializer

    def get_permissions(self):
        match self.action:
            case "retrieve" | "retrieve_related":
                return [IsAuthenticated(), SessionUserMayAccessInvocation()]
            case "create":
                return [SessionUserMayPerformInvocation()]
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
            elif hasattr(instance, "authorizedlinkaccount"):
                serializer = AuthorizedLinkAccountSerializer(
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
            elif hasattr(instance, "configuredlinkaddon"):
                serializer = ConfiguredLinkAddonSerializer(
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
        _invocation = (
            AddonOperationInvocation.objects.filter(pk=serializer.instance.pk)
            .select_related(
                *self._get_narrowed_down_selects(serializer),
                "thru_account___credentials",
            )
            .first()
        )
        if _invocation.thru_addon:
            _invocation.thru_addon.base_account = _invocation.thru_account
        _operation_type = _invocation.operation.operation_type
        match _operation_type:
            case AddonOperationType.REDIRECT | AddonOperationType.IMMEDIATE:
                perform_invocation__blocking(_invocation)
            case AddonOperationType.EVENTUAL:
                perform_invocation__celery.delay(_invocation.pk)
            case _:
                raise ValueError(f"unknown operation type: {_operation_type}")
        serializer.instance = _invocation

    def _get_narrowed_down_selects(self, serializer):
        addon_resource_name = serializer.initial_data.get(
            "thru_addon", serializer.initial_data.get("thru_account")
        )["type"]
        addon_type = addon_resource_name.split("-")[1]
        return [
            f"thru_addon__configured{addon_type}addon",
            f"thru_account__authorized{addon_type}account",
            f"thru_account__external_service__external{addon_type}service",
        ]
