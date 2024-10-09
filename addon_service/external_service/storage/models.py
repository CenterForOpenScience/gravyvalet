from enum import (
    Flag,
    auto,
)

from django.db import models

from addon_service.authorized_account.storage.models import AuthorizedStorageAccount
from addon_service.common.validators import (
    _validate_enum_value,
    validate_storage_imp_number,
)
from addon_service.external_service.models import ExternalService


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
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)

    int_supported_features = models.IntegerField(
        validators=[validate_supported_features], null=True
    )

    @property
    def supported_features(self) -> list[SupportedFeatures]:
        """get the enum representation of int_supported_features"""
        return SupportedFeatures(self.int_supported_features)

    @supported_features.setter
    def supported_features(self, new_supported_features: SupportedFeatures):
        """set int_authorized_capabilities without caring its int"""
        self.int_supported_features = new_supported_features.value

    def clean(self):
        super().clean()
        validate_storage_imp_number(self.int_addon_imp)

    @property
    def authorized_storage_accounts(self):
        return AuthorizedStorageAccount.objects.filter(external_service=self)

    class Meta:
        verbose_name = "External Storage Service"
        verbose_name_plural = "External Storage Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-storage-services"
