from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from addon_service.addon_imp.known import get_imp_by_number
from addon_service.addon_imp.models import AddonImpModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_storage_imp_number
from addon_service.credentials import (
    CredentialsFormats,
    validate_credentials_format,
)
from addon_toolkit.storage import StorageAddonImp

from .enums import ServiceTypes
from .validators import validate_service_type


class ExternalStorageService(AddonsServiceBaseModel):
    name = models.CharField(null=False)
    int_addon_imp = models.IntegerField(
        null=False,
        validators=[validate_storage_imp_number],
    )
    int_credentials_format = models.IntegerField(
        null=False,
        validators=[validate_credentials_format],
    )
    int_service_type = models.IntegerField(
        null=False,
        default=ServiceTypes.PUBLIC.value,
        validators=[validate_service_type],
    )
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)
    supported_scopes = ArrayField(models.CharField(), null=True, blank=True)
    api_base_url = models.URLField(blank=True, default="")

    oauth2_client_config = models.ForeignKey(
        "addon_service.OAuth2ClientConfig",
        on_delete=models.CASCADE,
        related_name="external_storage_services",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "External Storage Service"
        verbose_name_plural = "External Storage Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-storage-services"

    @property
    def addon_imp(self) -> AddonImpModel:
        return AddonImpModel(get_imp_by_number(self.int_addon_imp))

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

    @property
    def waterbutler_provider_key(self) -> str | None:
        _imp_cls = get_imp_by_number(self.int_addon_imp).imp_cls
        return (
            _imp_cls.waterbutler_provider_key
            if issubclass(_imp_cls, StorageAddonImp)
            else None
        )

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        if not self.configurable_api_root and not self.api_base_url:
            raise ValidationError("Public-only services must specify an api_base_url")
        if (
            self.credentials_format is CredentialsFormats.OAUTH2
            and not self.oauth2_client_config
        ):
            raise ValidationError("OAuth Services must link their Client Config")
