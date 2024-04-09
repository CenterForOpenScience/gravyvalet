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


class ExternalStorageService(AddonsServiceBaseModel):
    service_name = models.CharField(null=False)
    int_addon_imp = models.IntegerField(
        null=False,
        validators=[validate_storage_imp_number],
    )
    int_credentials_format = models.IntegerField(
        null=False,
        validators=[validate_credentials_format],
    )
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)
    auth_callback_url = models.URLField(null=False, default="")
    supported_scopes = ArrayField(models.CharField(), null=True, blank=True)

    oauth2_client_config = models.ForeignKey(
        "addon_service.OAuth2ClientConfig",
        on_delete=models.CASCADE,
        related_name="external_storage_services",
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

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        if (
            self.credentials_format is CredentialsFormats.OAUTH2
            and not self.oauth2_client_config
        ):
            raise ValidationError("OAuth Services must link their Client Config")
