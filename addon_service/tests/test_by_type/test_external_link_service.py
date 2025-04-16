from http import HTTPStatus
from unittest.mock import (
    MagicMock,
    patch,
)

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.external_service.link.views import ExternalLinkServiceViewSet
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
)
from addon_toolkit.interfaces.link import SupportedResourceTypes


def mock_get_link_addon_instance(*args, **kwargs):
    mock_instance = MagicMock()
    mock_instance.build_url_for_id = MagicMock(
        return_value="https://example.com/dataset/123"
    )
    mock_instance.get_external_account_id = MagicMock(return_value="test-account-id")
    return mock_instance


class TestExternalLinkServiceAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._els = _factories.ExternalLinkOAuth2ServiceFactory()

    def setUp(self):
        super().setUp()
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

    @property
    def _detail_path(self):
        return reverse("external-link-services-detail", kwargs={"pk": self._els.pk})

    @property
    def _list_path(self):
        return reverse("external-link-services-list")

    @property
    def _related_authorized_link_accounts_path(self):
        return reverse(
            "external-link-services-related",
            kwargs={
                "pk": self._els.pk,
                "related_field": "authorized_link_accounts",
            },
        )

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["auth_uri"], self._els.auth_uri)

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"post"},
            self._list_path: {"patch", "put", "post"},
            self._related_authorized_link_accounts_path: {"patch", "put", "post"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestExternalLinkServiceModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._els = _factories.ExternalLinkOAuth2ServiceFactory()

    def setUp(self):
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
        _resource_from_db = db.ExternalLinkService.objects.get(id=self._els.id)
        self.assertEqual(self._els.auth_uri, _resource_from_db.auth_uri)

    def test_authorized_link_accounts__empty(self):
        self.assertEqual(
            list(self._els.authorized_link_accounts.all()),
            [],
        )

    def test_authorized_link_accounts__several(self):
        _accounts = set(
            _factories.AuthorizedLinkAccountFactory.create_batch(
                size=3,
                external_service=self._els,
            )
        )
        self.assertEqual(
            set(self._els.authorized_link_accounts.all()),
            _accounts,
        )

    def test_supported_resource_types_property(self):
        self._els.supported_resource_types = SupportedResourceTypes.DATASET
        self._els.save()

        refreshed = db.ExternalLinkService.objects.get(id=self._els.id)
        self.assertEqual(
            refreshed.supported_resource_types, SupportedResourceTypes.DATASET
        )

        multi_type = SupportedResourceTypes.DATASET | SupportedResourceTypes.PROJECT
        self._els.supported_resource_types = multi_type
        self._els.save()

        refreshed = db.ExternalLinkService.objects.get(id=self._els.id)
        self.assertEqual(refreshed.supported_resource_types, multi_type)

    def test_validation__invalid_format(self):
        service = _factories.ExternalLinkOAuth2ServiceFactory()
        service.int_credentials_format = -1
        with self.assertRaises(ValidationError):
            service.save()

    def test_validation__unsupported_format(self):
        service = _factories.ExternalLinkOAuth2ServiceFactory()
        service.int_credentials_format = CredentialsFormats.UNSPECIFIED.value
        with self.assertRaises(ValidationError):
            service.save()

    def test_validation__oauth_creds_require_client_config(self):
        service = _factories.ExternalLinkOAuth2ServiceFactory(
            credentials_format=CredentialsFormats.OAUTH2
        )
        service.oauth2_client_config = None
        with self.assertRaises(ValidationError):
            service.save()


class TestExternalLinkServiceViewSet(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._els = _factories.ExternalLinkOAuth2ServiceFactory()
        cls._view = ExternalLinkServiceViewSet.as_view({"get": "retrieve"})
        cls._user = _factories.UserReferenceFactory()

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
        _resp = self._view(
            get_test_request(),
            pk=self._els.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)

        with self.subTest("Confirm expected keys"):
            self.assertIn("supported_resource_types", _resp.data.keys())
            self.assertIn("display_name", _resp.data.keys())
            self.assertIn("credentials_format", _resp.data.keys())

        with self.subTest("Confirm expected relationships"):
            relationship_fields = {
                key for key, value in _resp.data.items() if isinstance(value, dict)
            }
            self.assertIn("addon_imp", relationship_fields)

    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._els.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.OK)

    def test_wrong_user(self):
        _another_user = _factories.UserReferenceFactory()
        _resp = self._view(
            get_test_request(user=_another_user),
            pk=self._els.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)


class TestExternalLinkServiceRelatedView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._els = _factories.ExternalLinkOAuth2ServiceFactory()
        cls._related_view = ExternalLinkServiceViewSet.as_view(
            {"get": "retrieve_related"},
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

    def test_get_related(self):
        _resp = self._related_view(
            get_test_request(),
            pk=self._els.pk,
            related_field="addon_imp",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["name"], self._els.addon_imp.name)
