from http import HTTPStatus
from unittest.mock import (
    MagicMock,
    patch,
)

from django.test import TestCase
from django.urls import reverse
from itsdangerous import Signer
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.authorized_account.link.views import AuthorizedLinkAccountViewSet
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.service_types import ServiceTypes
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
    patch_encryption_key_derivation,
)
from addon_toolkit import AddonCapabilities
from addon_toolkit.credentials import (
    AccessKeySecretKeyCredentials,
    AccessTokenCredentials,
    UsernamePasswordCredentials,
)
from app import settings


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
            "type": "authorized-link-accounts",
            "attributes": {
                "display_name": display_name,
                "authorized_capabilities": capabilities,
                "api_base_url": api_root,
                "initiate_oauth": initiate_oauth,
            },
            "relationships": {
                "external_link_service": {
                    "data": {
                        "type": "external-link-services",
                        "id": str(external_service.id),
                    }
                },
            },
        }
    }
    credentials = credentials or MOCK_CREDENTIALS[external_service.credentials_format]
    if credentials:
        from addon_service.common import json_arguments

        payload["data"]["attributes"]["credentials"] = (
            json_arguments.json_for_dataclass(credentials)
        )
    return payload


def mock_get_link_addon_instance(*args, **kwargs):
    mock_instance = MagicMock()
    mock_instance.build_url_for_id = MagicMock(
        return_value="https://example.com/dataset/123"
    )
    mock_instance.get_external_account_id = MagicMock(return_value="test-account-id")
    return mock_instance


class TestAuthorizedLinkAccountAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ala = _factories.AuthorizedLinkAccountFactory()
        cls._user = cls._ala.account_owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = (
            Signer(settings.OSF_AUTH_COOKIE_SECRET).sign(self._user.user_uri).decode()
        )
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.instantiation_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance",
            mock_get_link_addon_instance,
        )
        self.instantiation_blocking_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance__blocking",
            mock_get_link_addon_instance,
        )
        self.instantiation_patcher.start()
        self.instantiation_blocking_patcher.start()
        self.addCleanup(self.instantiation_patcher.stop)
        self.addCleanup(self.instantiation_blocking_patcher.stop)

    @property
    def _detail_path(self):
        return reverse(
            "authorized-link-accounts-detail",
            kwargs={"pk": self._ala.pk},
        )

    @property
    def _list_path(self):
        return reverse("authorized-link-accounts-list")

    def _related_path(self, related_field):
        return reverse(
            "authorized-link-accounts-related",
            kwargs={
                "pk": self._ala.pk,
                "related_field": related_field,
            },
        )

    def test_get_detail(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["display_name"], self._ala.display_name)

    def test_post(self):
        external_service = _factories.ExternalLinkOAuth2ServiceFactory()
        self.assertFalse(external_service.authorized_link_accounts.exists())

        _resp = self.client.post(
            reverse("authorized-link-accounts-list"),
            _make_post_payload(
                external_service=external_service, display_name="test link account"
            ),
            format="vnd.api+json",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

        _from_db = external_service.authorized_link_accounts.get(id=_resp.data["id"])
        self.assertEqual(_from_db.display_name, "test link account")

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"put"},
            self._list_path: {"put"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestAuthorizedLinkAccountModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user,
        )

    def setUp(self):
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

        self.instantiation_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance",
            mock_get_link_addon_instance,
        )
        self.instantiation_blocking_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance__blocking",
            mock_get_link_addon_instance,
        )
        self.instantiation_patcher.start()
        self.instantiation_blocking_patcher.start()
        self.addCleanup(self.instantiation_patcher.stop)
        self.addCleanup(self.instantiation_blocking_patcher.stop)

    def test_can_load(self):
        _account_from_db = db.AuthorizedLinkAccount.objects.get(id=self._account.id)
        self.assertEqual(self._account.display_name, _account_from_db.display_name)

    def test_configured_link_addons__empty(self):
        self.assertEqual(
            list(self._account.configured_link_addons.all()),
            [],
        )

    def test_configured_link_addons__several(self):
        _addons = set(
            _factories.ConfiguredLinkAddonFactory.create_batch(
                size=3,
                base_account=self._account,
            )
        )
        self.assertEqual(
            set(self._account.configured_link_addons.all()),
            _addons,
        )

    def test_set_credentials__create(self):
        for creds_format in [
            CredentialsFormats.PERSONAL_ACCESS_TOKEN,
            CredentialsFormats.ACCESS_KEY_SECRET_KEY,
            CredentialsFormats.USERNAME_PASSWORD,
        ]:
            account = _factories.AuthorizedLinkAccountFactory(
                credentials_format=creds_format
            )
            with self.subTest(creds_format=creds_format):
                with patch_encryption_key_derivation():
                    account.credentials = MOCK_CREDENTIALS[creds_format]
                    account.save()

                refreshed = db.AuthorizedLinkAccount.objects.get(id=account.id)

                self.assertTrue(refreshed.credentials_available)

                with patch_encryption_key_derivation():
                    self.assertEqual(
                        refreshed.credentials,
                        MOCK_CREDENTIALS[creds_format],
                    )

    def test_capabilities(self):
        new_capabilities = AddonCapabilities.ACCESS | AddonCapabilities.UPDATE
        self._account.authorized_capabilities = new_capabilities
        self._account.save()

        refreshed = db.AuthorizedLinkAccount.objects.get(id=self._account.id)
        self.assertEqual(refreshed.authorized_capabilities, new_capabilities)


class TestAuthorizedLinkAccountViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user,
        )
        cls._view = AuthorizedLinkAccountViewSet.as_view({"get": "retrieve"})

        cls._addons = _factories.ConfiguredLinkAddonFactory.create_batch(
            size=2,
            base_account=cls._account,
        )

    def setUp(self):
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.instantiation_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance",
            mock_get_link_addon_instance,
        )
        self.instantiation_blocking_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance__blocking",
            mock_get_link_addon_instance,
        )
        self.instantiation_patcher.start()
        self.instantiation_blocking_patcher.start()
        self.addCleanup(self.instantiation_patcher.stop)
        self.addCleanup(self.instantiation_blocking_patcher.stop)

    def test_get(self):
        request = get_test_request(user=self._user)
        request.session = {"user_reference_uri": self._user.user_uri}
        request.COOKIES = {"osf": self._user.user_uri}
        _resp = self._view(
            request,
            pk=self._account.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)

        with self.subTest("Confirm expected keys"):
            expected_fields = {
                "authorized_capabilities",
                "authorized_operation_names",
                "credentials_available",
                "display_name",
                "api_base_url",
            }
            for field in expected_fields:
                self.assertIn(field, _resp.data.keys())

        with self.subTest("Confirm expected relationships"):
            relationship_fields = {
                key for key, value in _resp.data.items() if isinstance(value, dict)
            }
            for relation in ["account_owner", "external_link_service"]:
                self.assertIn(relation, relationship_fields)

    def test_owner_access(self):
        request = get_test_request(user=self._user)
        request.session = {"user_reference_uri": self._user.user_uri}
        request.COOKIES = {"osf": self._user.user_uri}
        _resp = self._view(
            request,
            pk=self._account.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)

    def test_wrong_user(self):
        _another_user = _factories.UserReferenceFactory()
        self._mock_osf.configure_assumed_caller(_another_user.user_uri)
        request = get_test_request(user=_another_user)
        request.session = {"user_reference_uri": _another_user.user_uri}
        request.COOKIES = {"osf": _another_user.user_uri}
        _resp = self._view(
            request,
            pk=self._account.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestCreateAuthorizedLinkAccount(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._external_service = _factories.ExternalLinkOAuth2ServiceFactory()

    def setUp(self):
        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = (
            Signer(settings.OSF_AUTH_COOKIE_SECRET).sign(self._user.user_uri).decode()
        )

        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.instantiation_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance",
            mock_get_link_addon_instance,
        )
        self.instantiation_blocking_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance__blocking",
            mock_get_link_addon_instance,
        )

        self.instantiation_patcher.start()
        self.instantiation_blocking_patcher.start()

        self.addCleanup(self.instantiation_patcher.stop)
        self.addCleanup(self.instantiation_blocking_patcher.stop)

    def test_create_account(self):
        external_service = _factories.ExternalLinkOAuth2ServiceFactory(
            service_type=ServiceTypes.PUBLIC | ServiceTypes.HOSTED,
        )
        self.assertFalse(external_service.authorized_link_accounts.exists())

        capabilities = ["ACCESS"]

        _resp = self.client.post(
            reverse("authorized-link-accounts-list"),
            _make_post_payload(
                external_service=external_service,
                display_name="Test Link Account",
                api_root="https://api.example.com",
                capabilities=capabilities,
                initiate_oauth=False,
            ),
            format="vnd.api+json",
        )

        self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

        self.assertEqual(_resp.data["display_name"], "Test Link Account")
        self.assertIn("ACCESS", _resp.data["authorized_capabilities"])

        account = db.AuthorizedLinkAccount.objects.get(id=_resp.data["id"])
        self.assertEqual(account.display_name, "Test Link Account")
        self.assertEqual(account.api_base_url, "https://api.example.com")
        self.assertEqual(account.external_service.id, external_service.id)
