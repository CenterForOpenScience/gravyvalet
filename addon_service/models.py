"""Import models here so they auto-detect for makemigrations"""

from addon_service.addon_imp.models import AddonImpModel
from addon_service.addon_operation.models import AddonOperationModel
from addon_service.addon_operation_invocation.models import AddonOperationInvocation
from addon_service.authorized_storage_account.models import AuthorizedStorageAccount
from addon_service.configured_storage_addon.models import ConfiguredStorageAddon
from addon_service.credentials.models import ExternalCredentials
from addon_service.external_storage_service.models import ExternalStorageService
from addon_service.authorized_citation_account.models import AuthorizedCitationAccount
from addon_service.configured_citation_addon.models import ConfiguredCitationAddon
from addon_service.external_citation_service.models import ExternalCitationService
from addon_service.oauth1.models import OAuth1ClientConfig
from addon_service.oauth2.models import (
    OAuth2ClientConfig,
    OAuth2TokenMetadata,
)
from addon_service.resource_reference.models import ResourceReference
from addon_service.user_reference.models import UserReference


__all__ = (
    "AddonImpModel",
    "AddonOperationInvocation",
    "AddonOperationModel",
    "AuthorizedStorageAccount",
    "ConfiguredStorageAddon",
    "ExternalCredentials",
    "ExternalStorageService",
    "OAuth2ClientConfig",
    "OAuth2TokenMetadata",
    "OAuth1ClientConfig",
    "ResourceReference",
    "UserReference",
    "AuthorizedCitationAccount",
    "ConfiguredCitationAddon",
    "ExternalCitationService",
)
