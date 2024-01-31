from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class CredentialsIssuer(AddonsServiceBaseModel):
    name = models.CharField(null=False)

    class Meta:
        verbose_name = "External Service"
        verbose_name_plural = "External Services"
        app_label = "addon_service"
