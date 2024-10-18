import urllib
from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.authorized_account.storage.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
    patch_encryption_key_derivation,
)
from addon_toolkit import (
    AddonCapabilities,
    json_arguments,
)
from addon_toolkit.credentials import (
    AccessKeySecretKeyCredentials,
    AccessTokenCredentials,
    UsernamePasswordCredentials,
)


VALID_CREDENTIALS_FORMATS = set(CredentialsFormats) - {CredentialsFormats.UNSPECIFIED}
NON_OAUTH_FORMATS = VALID_CREDENTIALS_FORMATS - {
    CredentialsFormats.OAUTH2,
    CredentialsFormats.OAUTH1A,
}

MOCK_CREDENTIALS = {
    CredentialsFormats.OAUTH2: None,
    CredentialsFormats.PERSONAL_ACCESS_TOKEN: AccessTokenCredentials(
        access_token="token"
    ),
    CredentialsFormats.ACCESS_KEY_SECRET_KEY: AccessKeySecretKeyCredentials(
        access_key="access",
        secret_key="secret",
    ),
    CredentialsFormats.USERNAME_PASSWORD: UsernamePasswordCredentials(
        username="me",
        password="unsafe",
    ),
    CredentialsFormats.DATAVERSE_API_TOKEN: AccessTokenCredentials(
        access_token="token"
    ),
}


def _make_post_payload(
    *,
    external_service,
    capabilities=None,
    credentials=None,
    api_root="",
    display_name="MY ACCOUNT MINE",
    initiate_oauth=True,
):
    capabilities = capabilities or [AddonCapabilities.ACCESS.name]
    payload = {
        "data": {
            "type": "authorized-storage-accounts",
            "attributes": {
                "display_name": display_name,
                "authorized_capabilities": capabilities,
                "api_base_url": api_root,
                "initiate_oauth": initiate_oauth,
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
    credentials = credentials or MOCK_CREDENTIALS[external_service.credentials_format]
    if credentials:
        payload["data"]["attributes"]["credentials"] = (
            json_arguments.json_for_dataclass(credentials)
        )
    return payload


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
        external_service = _factories.ExternalStorageOAuth2ServiceFactory()
        self.assertFalse(external_service.authorized_storage_accounts.exists())

        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(
                external_service=external_service, display_name="disploo"
            ),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

        _from_db = external_service.authorized_storage_accounts.get(id=_resp.data["id"])
        self.assertEqual(_from_db.display_name, "disploo")

    def test_post__sets_credentials(self):
        for creds_format in NON_OAUTH_FORMATS:
            external_service = _factories.ExternalStorageServiceFactory()
            external_service.int_credentials_format = creds_format.value
            external_service.save()

            _resp = self.client.post(
                reverse("authorized-storage-accounts-list"),
                _make_post_payload(
                    external_service=external_service, initiate_oauth=False
                ),
                format="vnd.api+json",
            )
            self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

            account = db.AuthorizedStorageAccount.objects.get(id=_resp.data["id"])
            with self.subTest(creds_format=creds_format):
                self.assertEqual(
                    account._credentials.decrypted_credentials,
                    MOCK_CREDENTIALS[creds_format],
                )

    def test_post__sets_auth_url(self):
        external_service = _factories.ExternalStorageOAuth2ServiceFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )

        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(external_service=external_service),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

        self.assertIn("auth_url", _resp.data)

    def tet_post__does_not_set_auth_url(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                external_service = _factories.ExternalStorageOAuth2ServiceFactory(
                    credentials_format=creds_format
                )

                _resp = self.client.post(
                    reverse("authorized-storage-accounts-list"),
                    _make_post_payload(external_service=external_service),
                    format="vnd.api+json",
                )
                self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

                self.assertNotIn("auth_url", _resp.data)

    def test_post__api_base_url__success(self):
        for service_type in [
            ServiceTypes.HOSTED,
            ServiceTypes.PUBLIC | ServiceTypes.HOSTED,
        ]:
            with self.subTest(service_type=service_type):
                service = _factories.ExternalStorageOAuth2ServiceFactory(
                    service_type=service_type
                )
                _resp = self.client.post(
                    reverse("authorized-storage-accounts-list"),
                    _make_post_payload(
                        external_service=service, api_root="https://api.my.service/"
                    ),
                    format="vnd.api+json",
                )
                with self.subTest("Creation succeeds"):
                    self.assertEqual(_resp.status_code, HTTPStatus.CREATED)
                with self.subTest("api_base_url set on account"):
                    account = db.AuthorizedStorageAccount.objects.get(
                        id=_resp.data["id"]
                    )
                    self.assertTrue(account._api_base_url)

    def test_post__api_base_url__invalid__required(self):
        service = _factories.ExternalStorageOAuth2ServiceFactory(
            service_type=ServiceTypes.HOSTED
        )
        service.api_base_url = ""
        service.save()
        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(external_service=service),
            format="vnd.api+json",
        )

        self.assertEqual(_resp.status_code, 400)

    def test_post__api_base_url__invalid__unsupported(self):
        service = _factories.ExternalStorageOAuth2ServiceFactory(
            service_type=ServiceTypes.PUBLIC
        )
        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(
                external_service=service, api_root="https://api.my.service/"
            ),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, 400)

    def test_post__api_base_url__invalid__bad_url(self):
        service = _factories.ExternalStorageOAuth2ServiceFactory(
            service_type=ServiceTypes.HOSTED
        )
        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"),
            _make_post_payload(external_service=service, api_root="not.a.url"),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, 400)

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
    UPDATED_CREDENTIALS = {
        CredentialsFormats.PERSONAL_ACCESS_TOKEN: AccessTokenCredentials(
            access_token="new_token"
        ),
        CredentialsFormats.ACCESS_KEY_SECRET_KEY: AccessKeySecretKeyCredentials(
            access_key="secret",
            secret_key="access",
        ),
        CredentialsFormats.USERNAME_PASSWORD: UsernamePasswordCredentials(
            username="you",
            password="moresafe",
        ),
        CredentialsFormats.DATAVERSE_API_TOKEN: AccessTokenCredentials(
            access_token="new_token"
        ),
    }
    INVALID_CREDENTIALS = {
        CredentialsFormats.PERSONAL_ACCESS_TOKEN: MOCK_CREDENTIALS[
            CredentialsFormats.USERNAME_PASSWORD
        ],
        CredentialsFormats.ACCESS_KEY_SECRET_KEY: MOCK_CREDENTIALS[
            CredentialsFormats.PERSONAL_ACCESS_TOKEN
        ],
        CredentialsFormats.USERNAME_PASSWORD: MOCK_CREDENTIALS[
            CredentialsFormats.ACCESS_KEY_SECRET_KEY
        ],
        CredentialsFormats.DATAVERSE_API_TOKEN: MOCK_CREDENTIALS[
            CredentialsFormats.ACCESS_KEY_SECRET_KEY
        ],
    }

    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner

    def setUp(self):
        self.enterContext(patch_encryption_key_derivation())

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
            "state": [self._asa.oauth2_token_metadata.state_token],
            "client_id": [self._asa.external_service.oauth2_client_config.client_id],
            "scope": self._asa.oauth2_token_metadata.authorized_scopes,
            "redirect_uri": [
                self._asa.external_service.oauth2_client_config.auth_callback_url
            ],
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
                self.assertIsNone(self._asa.auth_url)

    def test_auth_url__no_active_state_token(self):
        self.assertIsNotNone(self._asa.auth_url)
        oauth_meta = self._asa.oauth2_token_metadata
        oauth_meta.state_nonce = None
        oauth_meta.refresh_token = "refresh"
        oauth_meta.save()
        self.assertIsNone(self._asa.auth_url)

    # initiate_oauth2_flow

    def test_initiate_oauth2_flow(self):
        account = db.AuthorizedStorageAccount.objects.create(
            external_service=_factories.ExternalStorageOAuth2ServiceFactory(
                credentials_format=CredentialsFormats.OAUTH2
            ),
            account_owner=self._user,
            authorized_capabilities=AddonCapabilities.ACCESS,
        )
        account.initiate_oauth2_flow()
        with self.subTest("State Token set on OAuth credentials creation"):
            self.assertIsNotNone(account.oauth2_token_metadata.state_token)
        with self.subTest("Scopes set on OAuth credentials creation"):
            self.assertCountEqual(
                account.oauth2_token_metadata.authorized_scopes,
                account.external_service.supported_scopes,
            )

    # set credentials

    def test_set_credentials__oauth__fails_if_state_token_exists(self):
        account = _factories.AuthorizedStorageAccountFactory(
            credentials_format=CredentialsFormats.OAUTH2,
        )
        account.credentials = AccessTokenCredentials(access_token="nope")
        with self.assertRaises(ValidationError):
            account.save()
        account.refresh_from_db()  # Confirm transaction rollback
        self.assertIsNone(account._credentials)

    def test_set_credentials__create(self):
        for creds_format in NON_OAUTH_FORMATS:
            external_service = _factories.ExternalStorageOAuth2ServiceFactory(
                credentials_format=creds_format
            )
            account = db.AuthorizedStorageAccount(
                external_service=external_service,
                account_owner=self._user,
                authorized_capabilities=AddonCapabilities.ACCESS,
            )
            self.assertIsNone(account._credentials)
            mock_credentials = MOCK_CREDENTIALS[creds_format]
            account.credentials = mock_credentials
            account.save()
            with self.subTest(creds_format=creds_format):
                self.assertEqual(
                    account._credentials.decrypted_credentials,
                    mock_credentials,
                )

    def test_set_credentials__create__oauth(self):
        account = _factories.AuthorizedStorageAccountFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )
        self.assertIsNone(account._credentials)

        token_metadata = account.oauth2_token_metadata
        token_metadata.state_nonce = None
        token_metadata.refresh_token = "refresh"
        token_metadata.save()

        account.credentials = AccessTokenCredentials(access_token="yep")
        account.save()
        account.refresh_from_db()  # Confirm that changes were committed
        self.assertEqual(account.credentials.access_token, "yep")

    def test_set_credentials__update(self):
        for creds_format in NON_OAUTH_FORMATS:
            account = _factories.AuthorizedStorageAccountFactory(
                credentials_format=creds_format,
                credentials=MOCK_CREDENTIALS[creds_format],
            )
            original_creds_id = account._credentials.id
            updated_credentials = self.UPDATED_CREDENTIALS[creds_format]
            account.credentials = updated_credentials
            account.save()
            account.refresh_from_db()
            with self.subTest(creds_format=creds_format):
                with self.subTest("Credentials values updated"):
                    self.assertEqual(
                        account._credentials.decrypted_credentials,
                        updated_credentials,
                    )
                with self.subTest("Credentials updated in place"):
                    self.assertEqual(account._credentials.id, original_creds_id)

    def test_set_credentials__invalid(self):
        for creds_format in NON_OAUTH_FORMATS:
            with self.subTest(creds_format=creds_format):
                account = _factories.AuthorizedStorageAccountFactory(
                    credentials_format=creds_format,
                    credentials=MOCK_CREDENTIALS[creds_format],
                )
                invalid_credentials = self.INVALID_CREDENTIALS[creds_format]
                with self.assertRaises(ValidationError):
                    account.credentials = invalid_credentials


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
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: self._user.user_uri}
            ),
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
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: self._user.user_uri}
            ),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            {_datum["id"] for _datum in _resp.data},
            {_addon.pk for _addon in _addons},
        )
