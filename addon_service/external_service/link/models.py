from django.core.exceptions import ValidationError
from django.db import models

from addon_service.authorized_account.link.models import AuthorizedLinkAccount
from addon_service.common.validators import (
    _validate_enum_value,
    validate_link_imp_number,
)
from addon_service.external_service.models import ExternalService
from addon_toolkit.interfaces.link import SupportedResourceTypes


def validate_supported_features(value):
    _validate_enum_value(SupportedResourceTypes, value)


class ExternalLinkService(ExternalService):
    browser_base_url = models.URLField(blank=True, default="")
    int_supported_resource_types = models.BigIntegerField(
        validators=[validate_supported_features], null=True
    )

    @property
    def supported_resource_types(self) -> list[SupportedResourceTypes]:
        """get the enum representation of int_supported_features"""
        return SupportedResourceTypes(self.int_supported_resource_types)

    @supported_resource_types.setter
    def supported_resource_types(
        self, new_supported_resource_types: SupportedResourceTypes
    ):
        """set int_authorized_capabilities without caring its int"""
        self.int_supported_resource_types = new_supported_resource_types.value

    def clean(self):
        super().clean()
        validate_link_imp_number(self.int_addon_imp)
        if not self.api_base_url and not self.browser_base_url:
            raise ValidationError(
                "External Link Service should provide at least one of `browser_base_url` or `api_base_url`"
            )

    @property
    def authorized_link_accounts(self):
        return AuthorizedLinkAccount.objects.filter(external_service=self)

    class Meta:
        verbose_name = "External Link Service"
        verbose_name_plural = "External Link Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-link-services"
