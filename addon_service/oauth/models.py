from datetime import timedelta

from asgiref.sync import sync_to_async
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import (
    models,
    transaction,
)
from django.utils import timezone

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_toolkit.credentials import AccessTokenCredentials

from .utils import FreshTokenResult
from .validators import ensure_shared_client


class OAuth2ClientConfig(AddonsServiceBaseModel):
    """
    Model for storing attributes that are required for managing
    OAuth2 credentials exchanges with an ExternalService on behalf
    of a registered client (e.g. the OSF)
    """

    # The base uri for initiating OAuth2 credentials exchanges
    auth_uri = models.URLField(null=False)
    auth_callback_url = models.URLField(null=False)
    token_endpoint_url = models.URLField(null=False)
    # The registered ID of the OAuth client
    client_id = models.CharField(null=True)
    client_secret = models.CharField(null=True)

    class Meta:
        verbose_name = "OAuth2 Client Config"
        verbose_name_plural = "OAuth2 Client Configs"
        app_label = "addon_service"


class OAuth2TokenMetadataManager(models.Manager):
    def get_by_state_token(self, state_token: str):
        try:
            _pk, _state_nonce = state_token.split(".", maxsplit=1)
        except ValueError:
            raise ValueError('invalid state_token, expected "{pk}.{nonce}"')
        # may raise OAuth2TokenMetadata.DoesNotExist or OAuth2TokenMetadata.MultipleObjectsReturned
        return self.get(pk=_pk, state_nonce=_state_nonce)


class OAuth2TokenMetadata(AddonsServiceBaseModel):
    """
    Model for storing attribute that are related to an OAuth2 Access Token
    but are not actually used for authenticating with the external service.
    """

    objects = OAuth2TokenMetadataManager()  # custom manager

    # A one-time-use value to identify the initial auth request with the external service
    state_nonce = models.CharField(null=True, blank=True)
    # The token used to exchange access tokens
    refresh_token = models.CharField(null=True, blank=True, db_index=True)
    # The expiration time of the access token stored in Credentials
    access_token_expiration = models.DateTimeField(null=True, blank=True)
    # The scopes associated with the access token stored in Credentials
    authorized_scopes = ArrayField(models.CharField(), null=False)

    @property
    def state_token(self) -> str | None:
        return f"{self.pk}.{self.state_nonce}" if self.state_nonce else None

    @property
    def linked_accounts(self):
        return self.authorized_storage_accounts.all()

    @property
    def client_details(self):
        return self.linked_accounts[0].external_service.oauth2_client_config

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        if not self.pk:
            return

        ensure_shared_client(self)
        if self.state_nonce and self.refresh_token:
            raise ValidationError(
                "Error on OAuth2 Flow: state nonce and refresh token both present."
            )
        if not (self.state_nonce or self.refresh_token):
            raise ValidationError(
                "Error in OAuth2 Flow: Neither state nonce nor refresh token present."
            )

    @sync_to_async
    @transaction.atomic
    def update_with_fresh_token(self, fresh_token_result: FreshTokenResult):
        # update this record's fields
        self.state_nonce = None  # one-time-use, now used
        self.refresh_token = fresh_token_result.refresh_token
        if fresh_token_result.expires_in is None:
            self.access_token_expiration = None
        else:
            self.access_token_expiration = timezone.now() + timedelta(
                seconds=fresh_token_result.expires_in
            )
        if fresh_token_result.scopes is not None:
            self.authorized_scopes = fresh_token_result.scopes
        self.save()
        # update related records' fields
        _credentials = AccessTokenCredentials(
            access_token=fresh_token_result.access_token
        )
        for _account in tuple(self.linked_accounts):
            _account.credentials = _credentials
            _account.save()

    class Meta:
        verbose_name = "OAuth2 Token Metadata"
        verbose_name_plural = "OAuth2 Token Metadata"
        app_label = "addon_service"
