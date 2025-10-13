import json
from http import HTTPStatus
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from itsdangerous import Signer
from rest_framework.test import APITestCase

from addon_service.configured_addon.link.models import is_supported_resource_type
from addon_service.configured_addon.link.serializers import VerifiedLinkSerializer
from addon_service.tests import _factories
from addon_service.tests._helpers import MockOSF
from addon_toolkit.interfaces.link import SupportedResourceTypes
from app import settings


def mock_target_url(self):
    return f"https://example.com/dataset/{self.target_id}" if self.target_id else None


class TestNullResourceTypeValidator(TestCase):

    def test_validator_with_none(self):
        try:
            is_supported_resource_type(None)
        except ValidationError:
            self.fail("Validator raised ValidationError unexpectedly when given None")

    def test_validator_with_valid_types(self):
        try:
            is_supported_resource_type(SupportedResourceTypes.Dataset.value)
            is_supported_resource_type(SupportedResourceTypes.Journal.value)
            is_supported_resource_type(SupportedResourceTypes.Software.value)
        except ValidationError:
            self.fail("Validator raised ValidationError unexpectedly on valid types")

    def test_validator_with_invalid_types(self):
        with self.assertRaises(ValidationError):
            is_supported_resource_type(-999)

        combined = (
            SupportedResourceTypes.Dataset.value | SupportedResourceTypes.Journal.value
        )
        with self.assertRaises(ValidationError):
            is_supported_resource_type(combined)


class TestConfiguredLinkAddonWithNullFields(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()
        cls._authorized_account = _factories.AuthorizedLinkAccountFactory(
            account_owner=cls._user
        )

    def setUp(self):
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

        self.task_patcher = patch(
            "addon_service.configured_addon.link.models.app.send_task"
        )
        self.mock_task = self.task_patcher.start()
        self.addCleanup(self.task_patcher.stop)

        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.target_url_patcher.start()
        self.addCleanup(self.target_url_patcher.stop)

        self.mock_task.reset_mock()

    def test_create_with_null_fields(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
            int_resource_type=None,
        )

        self.mock_task.reset_mock()

        addon.refresh_from_db()
        self.assertIsNone(addon.target_id)

        self.assertIsNotNone(addon.int_resource_type)
        self.assertIsNotNone(addon.resource_type)

        self.mock_task.reset_mock()
        addon.save()
        doi_task_called = False
        for call in self.mock_task.call_args_list:
            if call[0][0] == "website.identifiers.tasks.task__update_verified_links":
                doi_task_called = True
                break

        self.assertFalse(
            doi_task_called,
            "DOI metadata task should not be called when fields are missing",
        )

    def test_resource_type_property_with_none(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
        )
        self.assertIsNotNone(addon.resource_type)

    def test_resource_type_setter_with_value(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
        )

        addon.resource_type = SupportedResourceTypes.Dataset
        addon.save()

        addon.refresh_from_db()
        self.assertEqual(addon.int_resource_type, SupportedResourceTypes.Dataset.value)
        self.assertEqual(addon.resource_type, SupportedResourceTypes.Dataset)

    def test_save_with_missing_fields(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
        )

        self.mock_task.reset_mock()
        addon.save()

        doi_task_called = False
        for call in self.mock_task.call_args_list:
            if call[0][0] == "website.identifiers.tasks.task__update_verified_links":
                doi_task_called = True
                break

        self.assertFalse(
            doi_task_called,
            "DOI metadata task should not be called when target_id is missing",
        )

    def test_save_with_target_id_missing(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
        )
        addon.resource_type = SupportedResourceTypes.Dataset

        self.mock_task.reset_mock()
        addon.save()

        doi_task_called = False
        for call in self.mock_task.call_args_list:
            if call[0][0] == "website.identifiers.tasks.task__update_verified_links":
                doi_task_called = True
                break

        self.assertFalse(
            doi_task_called,
            "DOI metadata task should not be called when target_id is missing",
        )

    def test_save_with_resource_type_missing(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id="test-id",
        )
        addon.int_resource_type = 0

        self.mock_task.reset_mock()
        addon.save()

        doi_called = False
        for call in self.mock_task.call_args_list:
            if (
                call[0][0] == "website.identifiers.tasks.task__update_verified_links"
                and call[1]["kwargs"]["target_guid"] == self._resource.guid
            ):
                doi_called = True

        self.assertFalse(
            doi_called, "DOI task should not be called when resource_type is missing"
        )

    def test_save_with_all_fields_present(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id="test-id",
        )
        addon.resource_type = SupportedResourceTypes.Dataset

        self.mock_task.reset_mock()
        addon.save()

        doi_called = False
        for call in self.mock_task.call_args_list:
            if (
                call[0][0] == "website.identifiers.tasks.task__update_verified_links"
                and call[1]["kwargs"]["target_guid"] == self._resource.guid
            ):
                doi_called = True

        self.assertTrue(
            doi_called, "DOI task should be called when all fields are present"
        )

    def test_target_url_with_null_target_id(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
        )

        self.assertIsNone(addon.target_url())


class TestConfiguredLinkAddonSerializerNullFields(APITestCase):
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
            target_id="test-id",
        )

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = (
            Signer(settings.OSF_AUTH_COOKIE_SECRET).sign(self._user.user_uri).decode()
        )
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

    def test_api_update_with_null_fields(self):
        self._addon.target_id = "test-id"
        self._addon.resource_type = SupportedResourceTypes.Dataset
        self._addon.save()
        request_data = {
            "data": {
                "id": str(self._addon.id),
                "type": "configured-link-addons",
                "attributes": {"target_id": None},
            }
        }

        response = self.client.patch(
            self._detail_path,
            data=json.dumps(request_data),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Response content: {response.content}"
        )

        self._addon.refresh_from_db()
        self.assertIsNone(self._addon.target_id)
        self.assertIsNotNone(self._addon.int_resource_type)


class TestVerifiedLinkSerializer(TestCase):

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
            target_id="test-id",
        )

    def setUp(self):
        self.target_url_patcher = patch(
            "addon_service.configured_addon.link.models.ConfiguredLinkAddon.target_url",
            mock_target_url,
        )
        self.target_url_patcher.start()
        self.addCleanup(self.target_url_patcher.stop)

    def test_serialize_with_all_values(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id="test-id",
        )
        addon.resource_type = SupportedResourceTypes.Dataset

        serializer = VerifiedLinkSerializer(addon)
        data = serializer.data

        self.assertEqual(data["target_id"], "test-id")
        self.assertEqual(data["resource_type"], "Dataset")
        self.assertEqual(data["target_url"], "https://example.com/dataset/test-id")
        self.assertEqual(
            data["service_name"],
            addon.base_account.external_service.external_service_name,
        )

    def test_serialize_with_null_values(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
        )

        serializer = VerifiedLinkSerializer(addon)
        data = serializer.data

        self.assertIsNone(data["target_id"])
        self.assertIsNotNone(data["resource_type"])
        self.assertIsNone(data["target_url"])
        self.assertEqual(
            data["service_name"],
            addon.base_account.external_service.external_service_name,
        )
