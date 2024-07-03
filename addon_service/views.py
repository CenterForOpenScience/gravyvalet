""" Import views/viewsets here for convenience """

from http import HTTPStatus

from django.db import transaction
from django.http import JsonResponse

from addon_service.addon_imp.views import AddonImpViewSet
from addon_service.addon_operation.views import AddonOperationViewSet
from addon_service.addon_operation_invocation.views import (
    AddonOperationInvocationViewSet,
)
from addon_service.authorized_storage_account.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.configured_storage_addon.views import ConfiguredStorageAddonViewSet
from addon_service.external_storage_service.views import ExternalStorageServiceViewSet
from addon_service.oauth.views import oauth2_callback_view
from addon_service.resource_reference.views import ResourceReferenceViewSet
from addon_service.user_reference.views import UserReferenceViewSet


@transaction.non_atomic_requests
async def status(request):
    """
    Handles status checks for the GV
    """
    try:
        _host = request.get_host()
    except Exception:
        _host = None
    return JsonResponse(
        {"host": _host, "s": request.is_secure()},
        json_dumps_params={"indent": 2},
        status=HTTPStatus.OK,
    )


__all__ = (
    "AddonImpViewSet",
    "AddonOperationInvocationViewSet",
    "AddonOperationViewSet",
    "AuthorizedStorageAccountViewSet",
    "ConfiguredStorageAddonViewSet",
    "ExternalStorageServiceViewSet",
    "ResourceReferenceViewSet",
    "UserReferenceViewSet",
    "oauth2_callback_view",
    "status",
)
