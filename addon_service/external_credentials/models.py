from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ExternalCredentials(AddonsServiceBaseModel):
    # TODO: Settle on encryption solution
    oauth_key = models.CharField(blank=True, null=True)

    # For OAuth1, this is usually the "oauth_token_secret"
    # For OAuth2, this is not used
    oauth_secret = models.CharField(blank=True, null=True)

    # Used for OAuth2 only
    refresh_token = models.CharField(blank=True, null=True)
    date_last_refreshed = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    # State token
    state_token = models.CharField(blank=True, null=True)

    class Meta:
        verbose_name = "External Credentials"
        verbose_name_plural = "External Credentials"
        app_label = "addon_service"
