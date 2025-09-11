from django.db import models

from addon_service.external_service.models import ExternalService

class ExternalRedirectService(ExternalService):
    redirect_url = models.URLField(blank=True, default="")

    class Meta:
        verbose_name = "External Redirect Service"
        verbose_name_plural = "External Redirect Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-redirect-services"
