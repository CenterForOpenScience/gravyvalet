""" Import views/viewsets here for convenience """

from addon_service.authorized_storage_account.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.configured_storage_addon.views import ConfiguredStorageAddonViewSet
from addon_service.external_storage_service.views import ExternalStorageServiceViewSet
from addon_service.resource_reference.views import ResourceReferenceViewSet
from addon_service.user_reference.views import UserReferenceViewSet
from addon_service.common.views import OauthCallbackView


__all__ = (
    "AuthorizedStorageAccountViewSet",
    "ConfiguredStorageAddonViewSet",
    "ExternalStorageServiceViewSet",
    "ResourceReferenceViewSet",
    "UserReferenceViewSet",
    "UserReferenceViewSet",
    "OauthCallbackView",
)
