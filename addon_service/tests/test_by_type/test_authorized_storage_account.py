import json
import urllib
from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.authorized_storage_account.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.credentials import CredentialsFormats
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
)
from addon_toolkit import AddonCapabilities


VALID_CREDENTIALS_FORMATS = set(CredentialsFormats) - {CredentialsFormats.UNSPECIFIED}
NON_OAUTH_FORMATS = VALID_CREDENTIALS_FORMATS - {CredentialsFormats.OAUTH2}

MOCK_CREDENTIALS_BLOBS = {
    CredentialsFormats.OAUTH2: {},
    CredentialsFormats.PERSONAL_ACCESS_TOKEN: {"access_token": "token"},
    CredentialsFormats.ACCESS_KEY_SECRET_KEY: {
        "access_key": "access",
        "secret_key": "secret",
    },
    CredentialsFormats.USERNAME_PASSWORD: {"username": "me", "password": "unsafe"},
}


def _make_post_payload(*, external_service, capabilities=None, credentials=None):
    return {
        "data": {
            "type": "authorized-storage-accounts",
            "attributes": {
                "authorized_capabilities": capabilities or ["ACCESS"],
                "credentials": credentials
                or MOCK_CREDENTIALS_BLOBS[external_service.credentials_format],
            },
            "relationships": {
                "external_storage_service": {
                    "data": {
                        "type": "external-storage-services",
                        "id": external_service.id,
                    }
                },
            },
        }
    }


class TestAuthorizedStorageAccountAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

    @property
    def _detail_path(self):
        return reverse(
            "authorized-storage-accounts-detail",
            kwargs={"pk": self._asa.pk},
        )

    @property
    def _list_path(self):
        return reverse("authorized-storage-accounts-list")

    def _related_path(self, related_field):
        return reverse(
            "authorized-storage-accounts-related",
            kwargs={
                "pk": self._asa.pk,
                "related_field": related_field,
            },
        )

    def test_get_detail(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            _resp.data["default_root_folder"],
            self._asa.default_root_folder,
        )

    def test_post(self):
        external_service = _factories.ExternalStorageServiceFactory()
        self.assertFalse(external_service.authorized_storage_accounts.exists())

        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(external_service=external_service),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, 201)

        self.assertTrue(
            external_service.authorized_storage_accounts.filter(
                id=json.loads(_resp.rendered_content)["data"]["id"]
            ).exists()
        )

    def test_post__sets_credentials(self):
        for creds_format in VALID_CREDENTIALS_FORMATS:
            with self.subTest(creds_format=creds_format):
                external_service = _factories.ExternalStorageServiceFactory()
                external_service.int_credentials_format = creds_format.value
                external_service.save()

                _resp = self.client.post(
                    reverse("authorized-storage-accounts-list"),
                    _make_post_payload(external_service=external_service),
                    format="vnd.api+json",
                )
                self.assertEqual(_resp.status_code, 201)

                account = db.AuthorizedStorageAccount.objects.get(
                    id=json.loads(_resp.rendered_content)["data"]["id"]
                )
                self.assertEqual(
                    account._credentials.credentials_blob,
                    MOCK_CREDENTIALS_BLOBS[creds_format],
                )

    def tet_post__sets_auth_url(self):
        external_service = _factories.ExternalStorageServiceFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )

        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(external_service=external_service),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, 201)

        self.assertIn(
            "auth_url", json.loads(_resp.rendered_content)["data"]["attributes"]
        )

    def tet_post__does_not_set_auth_url(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                external_service = _factories.ExternalStorageServiceFactory(
                    credentials_format=creds_format
                )

                _resp = self.client.post(
                    reverse("authorized-storage-accounts-list"),
                    _make_post_payload(external_service=external_service),
                    format="vnd.api+json",
                )
                self.assertEqual(_resp.status_code, 201)

                self.assertNotIn(
                    "auth_url", json.loads(_resp.rendered_content)["data"]["attributes"]
                )

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"post"},
            self._list_path: {"patch", "put", "get"},
            self._related_path("account_owner"): {"patch", "put", "post"},
            self._related_path("external_storage_service"): {"patch", "put", "post"},
            self._related_path("configured_storage_addons"): {"patch", "put", "post"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


# unit-test data model
class TestAuthorizedStorageAccountModel(TestCase):
    UPDATED_CREDENTIALS_BLOBS = {
        CredentialsFormats.PERSONAL_ACCESS_TOKEN: {"access_token": "new_token"},
        CredentialsFormats.ACCESS_KEY_SECRET_KEY: {
            "access_key": "secret",
            "secret_key": "access",
        },
        CredentialsFormats.USERNAME_PASSWORD: {
            "username": "you",
            "password": "moresafe",
        },
    }
    INVALID_CREDENTIALS_BLOBS = {
        CredentialsFormats.PERSONAL_ACCESS_TOKEN: MOCK_CREDENTIALS_BLOBS[
            CredentialsFormats.USERNAME_PASSWORD
        ],
        CredentialsFormats.ACCESS_KEY_SECRET_KEY: MOCK_CREDENTIALS_BLOBS[
            CredentialsFormats.PERSONAL_ACCESS_TOKEN
        ],
        CredentialsFormats.USERNAME_PASSWORD: MOCK_CREDENTIALS_BLOBS[
            CredentialsFormats.ACCESS_KEY_SECRET_KEY
        ],
    }

    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner

    def test_can_load(self):
        _resource_from_db = db.AuthorizedStorageAccount.objects.get(id=self._asa.id)
        self.assertEqual(self._asa.pk, _resource_from_db.pk)

    def test_configured_storage_addons__empty(self):
        self.assertEqual(
            list(self._asa.configured_storage_addons.all()),
            [],
        )

    def test_configured_storage_addons__several(self):
        _accounts = set(
            _factories.ConfiguredStorageAddonFactory.create_batch(
                size=3,
                base_account=self._asa,
            )
        )
        self.assertEqual(
            set(self._asa.configured_storage_addons.all()),
            _accounts,
        )

    # auth_url property

    def test_auth_url(self):
        parsed_url = urllib.parse.urlparse(self._asa.auth_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        self.assertEqual(
            base_url, self._asa.external_service.oauth2_client_config.auth_uri
        )
        expected_query_params = {
            "state": [self._asa.credentials.state_token],
            "client_id": [self._asa.external_service.oauth2_client_config.client_id],
            "scope": self._asa.credentials.authorized_scopes,
            "redirect_uri": [self._asa.external_service.auth_callback_url],
            "response_type": ["code"],
        }
        self.assertEqual(expected_query_params, urllib.parse.parse_qs(parsed_url.query))

    def test_auth_url__non_oauth_provider(self):
        self.assertIsNotNone(self._asa.auth_url)
        service = self._asa.external_service
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                service.int_credentials_format = creds_format.value
                service.save()
                del self._asa.credentials_format  # clear cached_property
                self.assertIsNone(self._asa.auth_url)

    def test_auth_url__no_active_state_token(self):
        self.assertIsNotNone(self._asa.auth_url)
        del self._asa.credentials  # clear cached_property
        oauth_meta = self._asa._credentials.oauth2_token_metadata
        oauth_meta.state_token = None
        oauth_meta.save()
        self.assertIsNone(self._asa.auth_url)

    # set_credentials

    def test_set_credentials__oauth2(self):
        external_service = _factories.ExternalStorageServiceFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )
        account = db.AuthorizedStorageAccount(
            external_storage_service=external_service,
            account_owner=self._user,
            authorized_capabilities=[AddonCapabilities.ACCESS],
        )

        account.set_credentials(api_credentials_blob={"access_token": "ignored"})
        with self.subTest("State Token set on OAuth credentials creation"):
            self.assertIsNotNone(account.credentials.state_token)
        with self.subTest("Scopes set on OAuth credentials creation"):
            self.assertCountEqual(
                account.credentials.authorized_scopes, external_service.default_scopes
            )
        with self.subTest("Provided OAuth credentials ignored"):
            self.assertIsNone(account.credentials.access_token)

    def test_set_credentials__oauth__update_fails(self):
        account = _factories.AuthorizedStorageAccountFactory(
            credentials_format=CredentialsFormats.OAUTH2,
        )
        self.assertIsNotNone(account.credentials)
        with self.assertRaises(ValueError):
            account.set_credentials()

    def test_set_credentials__create(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                external_service = _factories.ExternalStorageServiceFactory(
                    credentials_format=creds_format
                )
                account = db.AuthorizedStorageAccount(
                    external_storage_service=external_service,
                    account_owner=self._user,
                    authorized_capabilities=[AddonCapabilities.ACCESS],
                )
                self.assertIsNone(account._credentials)
                mock_credentials = MOCK_CREDENTIALS_BLOBS[creds_format]
                account.set_credentials(api_credentials_blob=mock_credentials)
                self.assertEqual(
                    account._credentials.credentials_blob, mock_credentials
                )

    def test_set_credentials__update(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                account = _factories.AuthorizedStorageAccountFactory(
                    credentials_format=creds_format,
                    credentials_dict=MOCK_CREDENTIALS_BLOBS[creds_format],
                )
                original_creds_id = account._credentials.id
                updated_credentials = self.UPDATED_CREDENTIALS_BLOBS[creds_format]
                account.set_credentials(api_credentials_blob=updated_credentials)
                account.refresh_from_db()
                with self.subTest("Credentials values updated"):
                    self.assertEqual(
                        account._credentials.credentials_blob, updated_credentials
                    )
                with self.subTest("Credentials updated in place"):
                    self.assertEqual(account._credentials.id, original_creds_id)

    def test_set_credentials__invalid(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                account = _factories.AuthorizedStorageAccountFactory(
                    credentials_format=creds_format,
                    credentials_dict=MOCK_CREDENTIALS_BLOBS[creds_format],
                )
                invalid_credentials = self.INVALID_CREDENTIALS_BLOBS[creds_format]
                with self.assertRaises(ValidationError):
                    account.set_credentials(api_credentials_blob=invalid_credentials)


# unit-test viewset (call the view with test requests)
class TestAuthorizedStorageAccountViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner
        cls._view = AuthorizedStorageAccountViewSet.as_view({"get": "retrieve"})

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

    def test_get(self):
        _resp = self._view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._asa.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "default_root_folder",
                "authorized_capabilities",
                "authorized_operation_names",
                "auth_url",
            },
        )
        self.assertEqual(
            _content["data"]["attributes"]["authorized_capabilities"],
            ["ACCESS"],
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "account_owner",
                "external_storage_service",
                "configured_storage_addons",
                "authorized_operations",
            },
        )

    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._asa.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    def test_wrong_user(self):
        _resp = self._view(
            get_test_request(cookies={settings.USER_REFERENCE_COOKIE: "wrong/10"}),
            pk=self._asa.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestAuthorizedStorageAccountRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner
        cls._related_view = AuthorizedStorageAccountViewSet.as_view(
            {"get": "retrieve_related"},
        )

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

    def test_get_related__empty(self):
        _resp = self._related_view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    def test_get_related__several(self):
        _addons = _factories.ConfiguredStorageAddonFactory.create_batch(
            size=5,
            base_account=self._asa,
        )
        _resp = self._related_view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_addon.pk) for _addon in _addons},
        )
