from django.core.exceptions import ValidationError
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ExternalCredentials(AddonsServiceBaseModel):
    # TODO: Settle on encryption solution
    credentials_blob = models.JSONField(null=False, blank=True, default=dict)

    # Attributes inherited from back-references:
    # authorized_storage_account (AuthorizedStorageAccount._credentials, One2One)

    class Meta:
        verbose_name = "External Credentials"
        verbose_name_plural = "External Credentials"
        app_label = "addon_service"

    @staticmethod
    def from_api_blob(api_credentials_blob):
        """Create ExternalCredentials entry based on the data passed by the API.

        Since the API is just passing a JSON blob, this enables us to perform any translation
        we may need to make to our own internal format.
        """
        return ExternalCredentials.objects.create(
            credentials_blob=dict(api_credentials_blob)
        )

    @property
    def authorized_accounts(self):
        """Returns the list of all accounts that point to this set of credentials.

        For now, this will just be a single AuthorizedStorageAccount, but in the future
        other types of accounts for the same user could point to the same set of credentials
        """
        try:
            return (self.authorized_storage_account,)
        except ExternalCredentials.authorized_storage_account.RelatedObjectDoesNotExist:
            return None

    @property
    def format(self):
        if not self.authorized_accounts:
            return None
        return self.authorized_accounts[0].external_service.credentials_format

    def _update(self, api_credentials_blob):
        """Update credentials based on API.
        This should only be called from Authorized*Account.set_credentials()
        """
        self.credentials_blob = dict(api_credentials_blob)
        self.save()

    def as_data(self):
        """Returns a Dataclass instance of the credentials for performnig Addon Operations.

        This space should be used for any translation from the at-rest format of the data
        to the field names used for the appropriate dataclass so that the dataclasses can
        be DB-agnostic.
        """
        return self.format.dataclass(**self.credentials_blob)

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        self._validate_credentials()

    def _validate_credentials(self):
        if not self.authorized_accounts:
            return
        try:
            self.as_data()
        except TypeError as e:
            raise ValidationError(e)
