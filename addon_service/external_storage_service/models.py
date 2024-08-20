from enum import (
    Flag,
    auto,
)

from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.abstract.external_storage.models import ExternalService
from addon_service.common.validators import (
    _validate_enum_value,
    validate_storage_imp_number,
)


class SupportedFeatures(Flag):
    ADD_UPDATE_FILES = auto()
    ADD_UPDATE_FILES_PARTIAL = auto()
    DELETE_FILES = auto()
    DELETE_FILES_PARTIAL = auto()
    FORKING = auto()
    LOGS = auto()
    PERMISSIONS = auto()
    REGISTERING = auto()
    FILE_VERSIONS = auto()


def validate_supported_features(value):
    _validate_enum_value(SupportedFeatures, value)


class ExternalStorageService(ExternalService):
    int_addon_imp = models.IntegerField(
        null=False,
        validators=[validate_storage_imp_number],
        verbose_name="Addon implementation",
    )
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)
    wb_key = models.CharField(null=False, blank=True, default="")
    oauth1_client_config = models.ForeignKey(
        "addon_service.OAuth1ClientConfig",
        on_delete=models.SET_NULL,
        related_name="external_storage_services",
        null=True,
        blank=True,
    )

    oauth2_client_config = models.ForeignKey(
        "addon_service.OAuth2ClientConfig",
        on_delete=models.SET_NULL,
        related_name="external_storage_services",
        null=True,
        blank=True,
    )
    int_supported_features = ArrayField(
        models.IntegerField(validators=[validate_supported_features]),
        null=True,
        blank=True,
    )

    @property
    def supported_features(self) -> list[SupportedFeatures]:
        """get the enum representation of int_supported_features"""
        return [SupportedFeatures(item) for item in self.int_supported_features]

    class Meta:
        verbose_name = "External Storage Service"
        verbose_name_plural = "External Storage Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-storage-services"
