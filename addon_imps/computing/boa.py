import logging

from boaapi.boa_client import (
    BOA_API_ENDPOINT,
    BoaClient,
    BoaException,
)
from django.core.exceptions import ValidationError

from addon_toolkit.interfaces import computing


logger = logging.getLogger(__name__)


class BoaComputingImp(computing.ComputingAddonClientRequestorImp):
    """sending compute jobs to Iowa State's Boa cluster."""

    @classmethod
    def confirm_credentials(cls, credentials):
        try:
            boa_client = cls.create_client(credentials)
            boa_client.close()
        except BoaException:
            raise ValidationError(
                "Fail to validate username and password for "
                "endpoint:({BOA_API_ENDPOINT})"
            )

    @staticmethod
    def create_client(credentials):
        boa_client = BoaClient(endpoint=BOA_API_ENDPOINT)
        boa_client.login(credentials.username, credentials.password)
        return boa_client
