from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from addon_service import models as db
from addon_service.credentials import CredentialsFormats
from addon_service.tests import _factories


class TestExternalCredentialsModel(TestCase):
    def test_oauth_state_token_generation(self):
        creds = db.ExternalCredentials.initiate_oauth2_flow(
            authorized_scopes=["scopes"]
        )
        with mock.patch("addon_service.credentials.models.token_urlsafe") as mock_token:
            mock_token.side_effect = [creds.oauth2_token_metadata.state_token, "abcde"]
            new_creds = db.ExternalCredentials.initiate_oauth2_flow(
                authorized_scopes=["scopes"]
            )

        with self.subTest("Multiple attempts at token creation in case of collision"):
            self.assertEqual(mock_token.call_count, 2)
            self.assertEqual(new_creds.oauth2_token_metadata.state_token, "abcde")

        with self.subTest("Colliding Tokens not stored in DB"):
            self.assertEqual(db.ExternalCredentials.objects.count(), 2)
            self.assertEqual(db.OAuth2TokenMetadata.objects.count(), 2)

    def test_oauth2_constraints(self):
        creds = _factories.AuthorizedStorageAccountFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )._credentials
        token_metadata = creds.oauth2_token_metadata
        token_metadata.state_token = None
        token_metadata.save()
        with self.subTest("Must have access token or state token"), self.assertRaises(
            ValidationError
        ):
            creds.save()

        token_metadata.state_token = "state"
        creds.credentials_blob = {"access_token": "access"}
        with self.subTest(
            "Cannot have access token and state token"
        ), self.assertRaises(ValidationError):
            creds.save()

        token_metadata.state_token = None
        token_metadata.save()
        creds.credentials_blob = {"access_token": "access"}
        with self.subTest(
            "Cannot have access token without refresh token"
        ), self.assertRaises(ValidationError):
            creds.save()
