import logging
import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

from boaapi.boa_client import (
    BOA_API_ENDPOINT,
    BoaException,
)
from django.core.exceptions import ValidationError

from addon_imps.computing.boa import BoaComputingImp
from addon_toolkit.credentials import UsernamePasswordCredentials
from addon_toolkit.interfaces.computing import ComputingConfig


logger = logging.getLogger(__name__)


class TestBoaComputingImp(unittest.IsolatedAsyncioTestCase):

    @patch.object(BoaComputingImp, "create_client")
    def setUp(self, create_client_mock):
        self.base_url = BOA_API_ENDPOINT
        self.config = ComputingConfig(external_api_url=self.base_url)
        self.client = MagicMock()
        self.credentials = UsernamePasswordCredentials(username="dog", password="woof")
        self.imp = BoaComputingImp(config=self.config, credentials=self.credentials)
        self.imp.client = self.client

    @patch.object(BoaComputingImp, "create_client")
    def test_confirm_credentials_success(self, create_client_mock):
        creds = UsernamePasswordCredentials(username="dog", password="woof")
        self.imp.confirm_credentials(creds)

        create_client_mock.assert_called_once_with(creds)
        create_client_mock.return_value.close.assert_called_once_with()

    @patch.object(BoaComputingImp, "create_client", side_effect=BoaException("nope"))
    def test_confirm_credentials_fail(self, create_client_mock):
        creds = UsernamePasswordCredentials(username="dog", password="woof")
        create_client_mock.return_value.side_effect = BoaException("could not login")
        with self.assertRaises(ValidationError):
            self.imp.confirm_credentials(creds)

        create_client_mock.assert_called_once_with(creds)

    @patch(f"{BoaComputingImp.__module__}.BoaClient")
    def test_create_client(self, mock_cls):
        mock_obj = MagicMock()
        mock_cls.return_value = mock_obj
        creds = UsernamePasswordCredentials(username="dog", password="woof")
        BoaComputingImp.create_client(creds)

        mock_cls.assert_called_once_with(endpoint=BOA_API_ENDPOINT)
        mock_obj.login.assert_called_once_with("dog", "woof")
