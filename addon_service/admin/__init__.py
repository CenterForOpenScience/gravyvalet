from django.contrib import admin

from addon_service import models
from addon_service.common import known_imps
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.external_service.storage.models import SupportedFeatures

from ._base import GravyvaletModelAdmin
from .decorators import linked_many_field


@admin.register(models.ExternalStorageService)
class ExternalStorageServiceAdmin(GravyvaletModelAdmin):
    list_display = ("display_name", "created", "modified")
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
    raw_id_fields = ("oauth2_client_config",)
    enum_choice_fields = {
        "int_addon_imp": known_imps.AddonImpNumbers,
        "int_credentials_format": CredentialsFormats,
        "int_service_type": ServiceTypes,
    }

    enum_multiple_choice_fields = {
        "int_supported_features": SupportedFeatures,
    }


@admin.register(models.ExternalCitationService)
class ExternalCitationServiceAdmin(GravyvaletModelAdmin):
    list_display = ("display_name", "created", "modified")
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
    raw_id_fields = ("oauth2_client_config",)
    enum_choice_fields = {
        "int_addon_imp": known_imps.AddonImpNumbers,
        "int_credentials_format": CredentialsFormats,
        "int_service_type": ServiceTypes,
    }


@admin.register(models.OAuth2ClientConfig)
@linked_many_field("external_storage_services")
class OAuth2ClientConfigAdmin(GravyvaletModelAdmin):
    readonly_fields = (
        "id",
        "created",
        "modified",
    )


@admin.register(models.OAuth1ClientConfig)
@linked_many_field("external_storage_services")
class OAuth1ClientConfigAdmin(GravyvaletModelAdmin):
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
