from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class OAuth2ClientConfig(AddonsServiceBaseModel):
    auth_uri = models.URLField(null=False)
    client_id = models.CharField(null=True)

    class Meta:
        verbose_name = "OAuth2 Client Config"
        verbose_name_plural = "OAuth2 Client Configs"
        app_label = "addon_service"


class OAuth2TokenMetadata(AddonsServiceBaseModel):
    state_token = models.CharField(null=True, blank=True, db_index=True)
    refresh_token = models.CharField(null=True, blank=True, db_index=True)
    auth_token_expiration = models.DateTimeField(null=True, blank=True)
    authorized_scopes = ArrayField(models.CharField(), null=False)

    class Meta:
        verbose_name = "OAuth2 Token Metadata"
        verbose_name_plural = "OAuth2 Token Metadata"
        app_label = "addon_service"
        constraints = [
            models.UniqueConstraint(fields=["state_token"], name="unique state token")
        ]
