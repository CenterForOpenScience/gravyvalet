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
from addon_service.configured_addon.link.models import is_supported_resource_type
from addon_service.configured_addon.link.views import ConfiguredLinkAddonViewSet
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
)
from addon_toolkit import AddonCapabilities
from addon_toolkit.interfaces.link import SupportedResourceTypes


def mock_target_url(self):
    return f"https://example.com/dataset/{self.target_id}" if self.target_id else None


def mock_get_link_addon_instance(*args, **kwargs):
    mock_instance = MagicMock()
    mock_instance.build_url_for_id = MagicMock(
        return_value="https://example.com/dataset/123"
    )
    mock_instance.get_external_account_id = MagicMock(return_value="test-account-id")
    return mock_instance


class TestConfiguredLinkAddonAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()
        cls._authorized_account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user
        )
        cls._addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=cls._resource,
            base_account=cls._authorized_account,
        )

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._resource.resource_uri, "admin"
        )
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.target_url_patcher.start()
        self.addCleanup(self.target_url_patcher.stop)

    @property
    def _detail_path(self):
        return reverse("configured-link-addons-detail", kwargs={"pk": self._addon.pk})

    @property
    def _list_path(self):
        return reverse("configured-link-addons-list")

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["target_id"], self._addon.target_id)
        self.assertEqual(_resp.data["resource_type"], self._addon.resource_type)

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._list_path: {"patch", "put"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestConfiguredLinkAddonModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._addon = _factories.ConfiguredLinkAddonFactory()

    def setUp(self):
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.target_url_patcher.start()
        self.addCleanup(self.target_url_patcher.stop)

    def test_can_load(self):
        _addon_from_db = db.ConfiguredLinkAddon.objects.get(id=self._addon.id)
        self.assertEqual(self._addon.target_id, _addon_from_db.target_id)
        self.assertEqual(self._addon.resource_type, _addon_from_db.resource_type)

    def test_resource_type_property(self):
        self._addon.resource_type = SupportedResourceTypes.Book
        self._addon.save()

        refreshed = db.ConfiguredLinkAddon.objects.get(id=self._addon.id)
        self.assertEqual(refreshed.resource_type, "Book")

        self._addon.resource_type = SupportedResourceTypes.Other
        self._addon.save()

        refreshed = db.ConfiguredLinkAddon.objects.get(id=self._addon.id)
        self.assertEqual(refreshed.resource_type, "Other")

    def test_validator_valid_types(self):
        try:
            is_supported_resource_type(SupportedResourceTypes.Other.value)
            is_supported_resource_type(SupportedResourceTypes.Journal.value)
            is_supported_resource_type(SupportedResourceTypes.Software.value)
        except ValidationError:
            self.fail("Validator raised ValidationError unexpectedly on valid types")

    def test_validator_invalid_type(self):
        with self.assertRaises(ValidationError):
            is_supported_resource_type(-999)

        combined = (
            SupportedResourceTypes.Other.value | SupportedResourceTypes.Journal.value
        )
        with self.assertRaises(ValidationError):
            is_supported_resource_type(combined)

    def test_validation_on_save(self):
        self._addon.int_resource_type = (
            SupportedResourceTypes.Other.value | SupportedResourceTypes.Journal.value
        )
        with self.assertRaises(ValidationError):
            self._addon.clean_fields()

        self._addon.int_resource_type = -999
        with self.assertRaises(ValidationError):
            self._addon.clean_fields()

    def test_target_url(self):
        addon = _factories.ConfiguredLinkAddonFactory()
        addon.target_id = ""
        self.assertIsNone(addon.target_url())

        addon.target_id = "test-id"
        self.assertEqual(addon.target_url(), "https://example.com/dataset/test-id")


class TestConfiguredLinkAddonViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()
        cls._authorized_account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user
        )
        cls._addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=cls._resource,
            base_account=cls._authorized_account,
        )
        cls._view = ConfiguredLinkAddonViewSet.as_view({"get": "retrieve"})

    def setUp(self):
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._resource.resource_uri, "admin"
        )
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.target_url_patcher.start()
        self.addCleanup(self.target_url_patcher.stop)

    def test_get(self):
        request = get_test_request(user=self._user)
        request.session = {"user_reference_uri": self._user.user_uri}

        _resp = self._view(
            request,
            pk=self._addon.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)

        with self.subTest("Confirm expected attributes"):
            self.assertEqual(_resp.data["target_id"], self._addon.target_id)
            self.assertEqual(_resp.data["resource_type"], self._addon.resource_type)
            self.assertIn("connected_operation_names", _resp.data)

        with self.subTest("Confirm expected relationships"):
            relationship_fields = {
                key for key, value in _resp.data.items() if isinstance(value, dict)
            }
            self.assertIn("base_account", relationship_fields)
            self.assertIn("authorized_resource", relationship_fields)

    def test_owner_access(self):
        request = get_test_request(user=self._user)
        request.session = {"user_reference_uri": self._user.user_uri}

        _resp = self._view(
            request,
            pk=self._addon.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)

    def test_wrong_user(self):
        _another_user = _factories.UserReferenceFactory()
        self._mock_osf.configure_assumed_caller(_another_user.user_uri)

        request = get_test_request(user=_another_user)
        request.session = {"user_reference_uri": _another_user.user_uri}

        _resp = self._view(
            request,
            pk=self._addon.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestCreateConfiguredLinkAddon(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()
        cls._authorized_account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user,
            authorized_capabilities=AddonCapabilities.ACCESS,
        )

    def setUp(self):
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._resource.resource_uri, "admin"
        )
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.instance_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance",
            mock_get_link_addon_instance,
        )
        self.instance_blocking_patcher = patch(
            "addon_service.addon_imp.instantiation.get_link_addon_instance__blocking",
            mock_get_link_addon_instance,
        )

        self.target_url_patcher.start()
        self.instance_patcher.start()
        self.instance_blocking_patcher.start()

        self.addCleanup(self.target_url_patcher.stop)
        self.addCleanup(self.instance_patcher.stop)
        self.addCleanup(self.instance_blocking_patcher.stop)

    def test_create_addon(self):
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._resource.resource_uri, "admin"
        )
        self._mock_osf.configure_assumed_caller(self._user.user_uri)

        request_data = {
            "data": {
                "type": "configured-link-addons",
                "attributes": {
                    "target_id": "some-target-id",
                    "resource_type": "DATASET",
                    "connected_capabilities": ["ACCESS"],
                    "authorized_resource_uri": self._resource.resource_uri,
                },
                "relationships": {
                    "base_account": {
                        "data": {
                            "type": "authorized-link-accounts",
                            "id": str(self._authorized_account.id),
                        }
                    },
                    "authorized_resource": {
                        "data": {
                            "type": "resource-references",
                            "id": str(self._resource.id),
                        }
                    },
                },
            }
        }

        _resp = self.client.post(
            reverse("configured-link-addons-list"),
            request_data,
            format="vnd.api+json",
        )

        self.assertEqual(_resp.status_code, HTTPStatus.CREATED)

        self.assertEqual(_resp.data["resource_type"], "Other")

        addon = db.ConfiguredLinkAddon.objects.get(id=_resp.data["id"])
        self.assertEqual(addon.target_id, "some-target-id")
        self.assertEqual(addon.resource_type, "Other")
