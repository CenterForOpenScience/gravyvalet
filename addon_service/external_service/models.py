from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common import known_imps
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.common.validators import (
    validate_credentials_format,
    validate_service_type,
)


class ExternalService(AddonsServiceBaseModel):
    display_name = models.CharField(null=False)
    int_credentials_format = models.IntegerField(
        null=False,
        validators=[validate_credentials_format],
        verbose_name="Credentials format",
    )
    int_service_type = models.IntegerField(
        null=False,
        default=ServiceTypes.PUBLIC.value,
        validators=[validate_service_type],
        verbose_name="Service type",
    )
    int_addon_imp = models.IntegerField(
        null=False,
        verbose_name="Addon implementation",
    )
    supported_scopes = ArrayField(models.CharField(), null=True, blank=True)
    api_base_url = models.URLField(blank=True, default="")
    wb_key = models.CharField(null=False, blank=True, default="")
    oauth1_client_config = models.ForeignKey(
        "addon_service.OAuth1ClientConfig",
        on_delete=models.SET_NULL,
        related_name="external_services",
        null=True,
        blank=True,
    )

    oauth2_client_config = models.ForeignKey(
        "addon_service.OAuth2ClientConfig",
        on_delete=models.SET_NULL,
        related_name="external_services",
        null=True,
        blank=True,
    )

    def __repr__(self):
        return f'<{self.__class__.__qualname__}(pk="{self.pk}", display_name="{self.display_name}")>'

    __str__ = __repr__

    @property
    def addon_imp(self) -> AddonImpModel:
        return AddonImpModel(known_imps.get_imp_by_number(self.int_addon_imp))

    @addon_imp.setter
    def addon_imp(self, value: AddonImpModel):
        self.int_addon_imp = known_imps.get_imp_number(value.imp_cls)

    @property
    def auth_uri(self):
        if self.credentials_format is not CredentialsFormats.OAUTH2:
            return None
        return self.oauth2_client_config.auth_uri

    @property
    def credentials_format(self):
        return CredentialsFormats(self.int_credentials_format)

    @property
    def service_type(self):
        return ServiceTypes(self.int_service_type)

    @property
    def configurable_api_root(self):
        return ServiceTypes.HOSTED in self.service_type

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        if not self.configurable_api_root and not self.api_base_url:
            raise ValidationError("Public-only services must specify an api_base_url")
        if (
            self.credentials_format is CredentialsFormats.OAUTH2
            and not self.oauth2_client_config
        ):
            raise ValidationError("OAuth Services must link their Client Config")
