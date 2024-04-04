""" Import models here so they auto-detect for makemigrations """

from addon_service.addon_imp.models import AddonImpModel
from addon_service.addon_operation.models import AddonOperationModel
from addon_service.addon_operation_invocation.models import AddonOperationInvocation
from addon_service.authorized_storage_account.models import AuthorizedStorageAccount
from addon_service.configured_storage_addon.models import ConfiguredStorageAddon
from addon_service.credentials_issuer.models import CredentialsIssuer
from addon_service.external_account.models import ExternalAccount
from addon_service.external_credentials.models import ExternalCredentials
from addon_service.external_storage_service.models import ExternalStorageService
from addon_service.resource_reference.models import ResourceReference
from addon_service.user_reference.models import UserReference


__all__ = (
    "AddonImpModel",
    "AddonOperationInvocation",
    "AddonOperationModel",
    "AuthorizedStorageAccount",
    "ConfiguredStorageAddon",
    "CredentialsIssuer",
    "ExternalAccount",
    "ExternalCredentials",
    "ExternalStorageService",
    "ResourceReference",
    "UserReference",
)
