from enum import (
    Flag,
    auto,
)

from django.db import models

from addon_service.common.validators import (
    _validate_enum_value,
    validate_computing_imp_number,
)
from addon_service.external_service.models import ExternalService


class ComputingSupportedFeatures(Flag):
    ADD_UPDATE_FILES_PARTIAL = auto()
    FORKING_PARTIAL = auto()
    LOGS_PARTIAL = auto()
    PERMISSIONS_PARTIAL = auto()
    REGISTERING_PARTIAL = auto()


def validate_supported_features(value):
    _validate_enum_value(ComputingSupportedFeatures, value)


class ExternalComputingService(ExternalService):
    int_supported_features = models.IntegerField(
        validators=[validate_supported_features],
        null=True,
    )

    @property
    def supported_features(self) -> list[ComputingSupportedFeatures]:
        """get the enum representation of int_supported_features"""
        return ComputingSupportedFeatures(self.int_supported_features)

    @supported_features.setter
    def supported_features(self, new_supported_features: ComputingSupportedFeatures):
        """set int_authorized_capabilities without caring its int"""
        validate_computing_imp_number(self.int_addon_imp)
        self.int_supported_features = new_supported_features.value

    def clean(self):
        super().clean()
        validate_computing_imp_number(self.int_addon_imp)

    class Meta:
        verbose_name = "External Computing Service"
        verbose_name_plural = "External Computing Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-computing-services"
