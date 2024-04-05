from secrets import token_urlsafe

from django.core.exceptions import ValidationError
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.oauth import OAuth2TokenMetadata

from . import CredentialsFormats


_CREDENTIALS_VALUE_FIELDS = [
    "username",
    "pwd",
    "service_host",
    "access_key",
    "secret_key",
    "oauth_access_token",
]


class ExternalCredentials(AddonsServiceBaseModel):
    # TODO: Settle on encryption solution
    credentials_blob = models.JSONField(null=False, blank=True, default=dict)

    # Attributes inherited from back-references:
    # authorized_storage_account (AuthorizedStorageAccount._credentials, One2One)
    # oauth2_token_metadata (OAuth2TokenMetadata.token_source, One2One)

    class Meta:
        verbose_name = "External Credentials"
        verbose_name_plural = "External Credentials"
        app_label = "addon_service"

    @property
    def authorized_accounts(self):
        try:
            return (self.authorized_storage_account,)
        except ExternalCredentials.authorized_storage_account.RelatedObjectDoesNotExist:
            return None

    @staticmethod
    def from_api_blob(api_credentials_blob):
        """Create ExternalCredentials entry based on the data passed by the API.

        Since the API is just passing a JSON blob, this enables us to perform any translation
        we may need to make to our own internal format.
        """
        return ExternalCredentials.objects.create(
            credentials_blob=dict(api_credentials_blob)
        )

    @staticmethod
    def initiate_oauth2_flow(authorized_scopes):
        """Function for initiating the flow for retrieving OAuth2 credentials"""
        creds = ExternalCredentials.objects.create(credentials_blob={})
        OAuth2TokenMetadata.objects.create(
            token_source=creds,
            authorized_scopes=authorized_scopes,
            state_token=token_urlsafe(16),
        )
        return creds

    @property
    def format(self):
        if not self.authorized_accounts:
            return None
        return self.authorized_accounts[0].external_service.credentials_format

    def _update(self, api_credentials_blob):
        """Update credentials based on API.
        This should only be called from Authorized*Account.set_credentials()
        """
        if self.format is CredentialsFormats.OAUTH2:
            raise ValueError("Cannot direcly update OAuth credentials")
        self._credentials_blob = dict(api_credentials_blob)
        self.save()

    def as_data(self):
        """Returns a Dataclass instance of the credentials for performnig Addon Operations.

        This space should be used for any translation from the at-rest format of the data
        to the field names used for the appropriate dataclass so that the dataclasses can
        be DB-agnostic.
        """
        match self.format:
            case None:
                return None
            case CredentialsFormats.OAUTH2:
                return self.format.dataclass(
                    **self.credentials_blob,
                    **self.oauth2_token_metadata.as_dataclass_kwargs(),
                )
            case _:
                return self.format.dataclass(**self.credentials_blob)

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        self._validate_credentials()

    def _validate_credentials(self):
        if not self.authorized_accounts:
            return  # Credentials may not be associated with an account to start

        try:
            data_representation = self.as_data()
        except TypeError as e:
            raise ValidationError(e)
        data_representation.validate()
