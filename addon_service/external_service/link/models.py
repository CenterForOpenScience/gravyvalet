from enum import (
    Flag,
    auto,
)

from django.db import models

from addon_service.authorized_account.link.models import AuthorizedLinkAccount
from addon_service.common.validators import (
    _validate_enum_value,
    validate_link_imp_number,
)
from addon_service.external_service.models import ExternalService


class SupportedResourceTypes(Flag):
    ADD_UPDATE_FILES = auto()
    ADD_UPDATE_FILES_PARTIAL = auto()
    DELETE_FILES = auto()
    DELETE_FILES_PARTIAL = auto()
    FORKING = auto()
    LOGS = auto()
    PERMISSIONS = auto()
    REGISTERING = auto()
    FILE_VERSIONS = auto()
    COPY_INTO = auto()
    DOWNLOAD_AS_ZIP = auto()


def validate_supported_features(value):
    _validate_enum_value(SupportedResourceTypes, value)


class ExternalLinkService(ExternalService):
    int_supported_resource_types = models.IntegerField(
        validators=[validate_supported_features], null=True
    )

    @property
    def supported_resource_types(self) -> list[SupportedResourceTypes]:
        """get the enum representation of int_supported_features"""
        return SupportedResourceTypes(self.int_supported_features)

    @supported_resource_types.setter
    def supported_resource_types(
        self, new_supported_resource_types: SupportedResourceTypes
    ):
        """set int_authorized_capabilities without caring its int"""
        self.int_supported_features = new_supported_resource_types.value

    def clean(self):
        super().clean()
        validate_link_imp_number(self.int_addon_imp)

    @property
    def authorized_link_accounts(self):
        return AuthorizedLinkAccount.objects.filter(external_service=self)

    class Meta:
        verbose_name = "External Link Service"
        verbose_name_plural = "External Link Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-link-services"
