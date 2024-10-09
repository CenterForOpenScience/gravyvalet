""" Import views/viewsets here for convenience """

from http import HTTPStatus

from django.db import transaction
from django.http import JsonResponse

from addon_service.addon_imp.views import AddonImpViewSet
from addon_service.addon_operation.views import AddonOperationViewSet
from addon_service.addon_operation_invocation.views import (
    AddonOperationInvocationViewSet,
)
from addon_service.authorized_account.citation.views import (
    AuthorizedCitationAccountViewSet,
)
from addon_service.authorized_account.storage.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.configured_addon.citation.views import ConfiguredCitationAddonViewSet
from addon_service.configured_addon.storage.views import ConfiguredStorageAddonViewSet
from addon_service.external_service.citation.views import ExternalCitationServiceViewSet
from addon_service.external_service.storage.views import ExternalStorageServiceViewSet
from addon_service.oauth1.views import oauth1_callback_view
from addon_service.oauth2.views import oauth2_callback_view
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
    "AuthorizedCitationAccountViewSet",
    "ConfiguredCitationAddonViewSet",
    "ExternalCitationServiceViewSet",
    "AuthorizedStorageAccountViewSet",
    "ConfiguredStorageAddonViewSet",
    "ExternalStorageServiceViewSet",
    "ResourceReferenceViewSet",
    "UserReferenceViewSet",
    "oauth2_callback_view",
    "oauth1_callback_view",
    "status",
)
