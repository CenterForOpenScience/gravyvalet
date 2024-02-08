""" Import serializers here for convenience """

from addon_service.authorized_storage_account.serializers import (
    AuthorizedStorageAccountSerializer,
)
from addon_service.configured_storage_addon.serializers import (
    ConfiguredStorageAddonSerializer,
)
from addon_service.external_storage_service.serializers import (
    ExternalStorageServiceSerializer,
)
from addon_service.resource_reference.serializers import ResourceReferenceSerializer
from addon_service.user_reference.serializers import UserReferenceSerializer


__all__ = (
    "AuthorizedStorageAccountSerializer",
    "ConfiguredStorageAddonSerializer",
    "ExternalStorageServiceSerializer",
    "ResourceReferenceSerializer",
    "UserReferenceSerializer",
)
