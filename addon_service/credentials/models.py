from django.core.exceptions import ValidationError
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.dibs import dibs
from addon_toolkit.credentials import Credentials
from addon_toolkit.json_arguments import json_for_dataclass

from . import encryption


class ExternalCredentials(AddonsServiceBaseModel):
    encrypted_json = models.BinaryField()
    _salt = models.BinaryField()
    _scrypt_block_size = models.IntegerField()
    _scrypt_cost_log2 = models.IntegerField()
    _scrypt_parallelization = models.IntegerField()

    # Attributes inherited from back-references:
    # storage (AuthorizedStorageAccount._credentials, One2One)

    class Meta:
        verbose_name = "External Credentials"
        verbose_name_plural = "External Credentials"
        app_label = "addon_service"
        indexes = (
            models.Index(fields=["modified"]),  # for schedule_encryption_rotation
        )

    @classmethod
    def new(cls):
        # initialize key-parameter fields with fresh defaults
        _new = cls()
        _new._key_parameters = encryption.KeyParameters()
        return _new

    ###
    # public encryption-related methods

    @property
    def decrypted_credentials(self) -> Credentials:
        """Returns a Dataclass instance of the credentials for performing Addon Operations."""
        return self.format.dataclass(**self._decrypted_json)

    @decrypted_credentials.setter
    def decrypted_credentials(self, value: Credentials):
        self._decrypted_json = json_for_dataclass(value)

    def rotate_encryption(self):
        with dibs(self):
            self.encrypted_json, self._key_parameters = (
                encryption.pls_rotate_encryption(
                    encrypted=self.encrypted_json,
                    stored_params=self._key_parameters,
                )
            )
            self.save()

    ###
    # private encryption-related methods

    @property
    def _decrypted_json(self):
        return encryption.pls_decrypt_json(self.encrypted_json, self._key_parameters)

    @_decrypted_json.setter
    def _decrypted_json(self, value):
        self.encrypted_json = encryption.pls_encrypt_json(value, self._key_parameters)

    @property
    def _key_parameters(self) -> encryption.KeyParameters:
        return encryption.KeyParameters(
            salt=self._salt,
            scrypt_block_size=self._scrypt_block_size,
            scrypt_cost_log2=self._scrypt_cost_log2,
            scrypt_parallelization=self._scrypt_parallelization,
        )

    @_key_parameters.setter
    def _key_parameters(self, value: encryption.KeyParameters) -> None:
        self._salt = value.salt
        self._scrypt_block_size = value.scrypt_block_size
        self._scrypt_cost_log2 = value.scrypt_cost_log2
        self._scrypt_parallelization = value.scrypt_parallelization

    # END encryption-related methods
    ###

    @property
    def authorized_accounts(self):
        """Returns the list of all accounts that point to this set of credentials.

        For now, this will just be a single AuthorizedStorageAccount, but in the future
        other types of accounts for the same user could point to the same set of credentials
        """
        try:
            return [
                *filter(
                    bool,
                    [
                        getattr(self, "authorized_account", None),
                        getattr(self, "temporary_authorized_account", None),
                    ],
                )
            ]
        except ExternalCredentials.authorized_storage_account.RelatedObjectDoesNotExist:
            return None

    @property
    def format(self):
        if not self.authorized_accounts:
            return None
        return self.authorized_accounts[0].external_service.credentials_format

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        self._validate_credentials()

    def _validate_credentials(self):
        if not self.authorized_accounts:
            return
        try:
            self.decrypted_credentials
        except TypeError as e:
            raise ValidationError(e)
