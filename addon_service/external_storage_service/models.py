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
    default_scopes = ArrayField(models.CharField(), null=True, blank=True)
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)
    callback_url = models.URLField(null=False, default="")

    oauth_client_config = models.ForeignKey(
        "addon_service.OAuthClientConfig",
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
        return self.oauth_client_config.auth_uri

    @property
    def credentials_format(self):
        return CredentialsFormats(self.int_credentials_format)

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        if (
            self.credentials_format is CredentialsFormats.OAuth2
            and not self.oauth_client_config
        ):
            raise ValidationError("OAuth Services must link their Client Config")
