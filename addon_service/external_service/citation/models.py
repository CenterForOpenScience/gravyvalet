from enum import (
    Flag,
    auto,
)

from django.db import models

from addon_service.common.validators import (
    _validate_enum_value,
    validate_citation_imp_number,
)
from addon_service.external_service.models import ExternalService


class CitationSupportedFeatures(Flag):
    FORKING_PARTIAL = auto()
    PERMISSIONS_PARTIAL = auto()


def validate_supported_features(value):
    _validate_enum_value(CitationSupportedFeatures, value)


class ExternalCitationService(ExternalService):
    int_supported_features = models.IntegerField(
        validators=[validate_supported_features],
        null=True,
    )

    @property
    def supported_features(self) -> list[CitationSupportedFeatures]:
        """get the enum representation of int_supported_features"""
        return CitationSupportedFeatures(self.int_supported_features)

    @supported_features.setter
    def supported_features(self, new_supported_features: CitationSupportedFeatures):
        """set int_authorized_capabilities without caring its int"""
        validate_citation_imp_number(self.int_addon_imp)
        self.int_supported_features = new_supported_features.value

    def clean(self):
        super().clean()

    class Meta:
        verbose_name = "External Citation Service"
        verbose_name_plural = "External Citation Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-citation-services"
