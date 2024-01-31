from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class CredentialsIssuer(AddonsServiceBaseModel):
    """
    Represents the credentials for an external service in the Addons Service.
    """
    name = models.CharField(max_length=255, blank=False, null=False)

    class Meta:
        verbose_name = "External Service"
        verbose_name_plural = "External Services"
        app_label = "addon_service"
