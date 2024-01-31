""" Import views/viewsets here for convenience """

from addon_service.authorized_storage_account.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.configured_storage_addon.views import ConfiguredStorageAddonViewSet
from addon_service.external_storage_service.views import ExternalStorageServiceViewSet
from addon_service.internal_resource.views import InternalResourceViewSet
from addon_service.internal_user.views import InternalUserViewSet


__all__ = (
    "AuthorizedStorageAccountViewSet",
    "ConfiguredStorageAddonViewSet",
    "ExternalStorageServiceViewSet",
    "InternalResourceViewSet",
    "InternalUserViewSet",
)
