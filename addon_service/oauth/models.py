from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class OAuth2ClientConfig(AddonsServiceBaseModel):
    """
    Model for storing attributes that are required for managing
    OAuth2 credentials exchanges with an ExternalService on behalf
    of a registered client (e.g. the OSF)
    """

    # The base uri for initiating OAuth2 credentials exchanges
    auth_uri = models.URLField(null=False)
    # The registered ID of the OAuth client
    client_id = models.CharField(null=True)

    class Meta:
        verbose_name = "OAuth2 Client Config"
        verbose_name_plural = "OAuth2 Client Configs"
        app_label = "addon_service"


class OAuth2TokenMetadata(AddonsServiceBaseModel):
    """
    Model for storing attribute that are related to an OAuth2 Access Token
    but are not actually used for authenticating with the external service.
    """

    # The token used to identify the initiatl auth request with the external service
    state_token = models.CharField(null=True, blank=True, db_index=True)
    # The unique ID of the user on the external sservice
    user_id = models.CharField(null=True, blank=True)
    # The token used to exchange access tokens
    refresh_token = models.CharField(null=True, blank=True, db_index=True)
    # The expiration time of the access token stored in Credentials
    access_token_expiration = models.DateTimeField(null=True, blank=True)
    # The scopes associated with the access token stored in Credentials
    authorized_scopes = ArrayField(models.CharField(), null=False)

    class Meta:
        verbose_name = "OAuth2 Token Metadata"
        verbose_name_plural = "OAuth2 Token Metadata"
        app_label = "addon_service"
        constraints = [
            models.UniqueConstraint(fields=["state_token"], name="unique state token")
        ]
