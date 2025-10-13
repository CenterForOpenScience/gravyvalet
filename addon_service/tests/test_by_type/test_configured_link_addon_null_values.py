import json
from http import HTTPStatus
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from itsdangerous import Signer
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.configured_addon.link.serializers import (
    ConfiguredLinkAddonSerializer,
)
from addon_service.tests import _factories
from addon_service.tests._helpers import MockOSF
from addon_toolkit import AddonCapabilities
from addon_toolkit.interfaces.link import SupportedResourceTypes
from app import settings


def mock_target_url(self):
    return f"https://example.com/dataset/{self.target_id}" if self.target_id else None


class TestConfiguredLinkAddonNullValues(TestCase):
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

    def test_resource_type_setter_with_none(self):
        addon = _factories.ConfiguredLinkAddonFactory()

        addon.resource_type = SupportedResourceTypes.Other
        addon.save()
        refreshed = db.ConfiguredLinkAddon.objects.get(id=addon.id)
        self.assertEqual(refreshed.resource_type, SupportedResourceTypes.Other)

        addon.resource_type = None
        addon.save()

        refreshed = db.ConfiguredLinkAddon.objects.get(id=addon.id)
        self.assertEqual(
            refreshed.int_resource_type, SupportedResourceTypes.Other.value
        )


class TestConfiguredLinkAddonSerializerNullValues(APITestCase):
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

    def test_serializer_with_null_target_id(self):
        serializer = ConfiguredLinkAddonSerializer(
            data={
                "target_id": None,
                "connected_capabilities": [AddonCapabilities.ACCESS.name],
                "base_account": {
                    "id": self._authorized_account.id,
                    "type": "authorized-link-accounts",
                },
                "authorized_resource": self._resource.resource_uri,
            },
            context={"request": None},
        )

        self.assertTrue(
            serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        )

    def test_serializer_with_null_resource_type(self):
        serializer = ConfiguredLinkAddonSerializer(
            data={
                "resource_type": None,
                "connected_capabilities": [AddonCapabilities.ACCESS.name],
                "base_account": {
                    "id": self._authorized_account.id,
                    "type": "authorized-link-accounts",
                },
                "authorized_resource": self._resource.resource_uri,
            },
            context={"request": None},
        )

        self.assertTrue(
            serializer.is_valid(), f"Serializer errors: {serializer.errors}"
        )

    def test_api_update_with_null_values(self):
        self._addon.target_id = "test-dataset-id"
        self._addon.resource_type = SupportedResourceTypes.Other
        self._addon.save()

        request_data = {
            "data": {
                "id": str(self._addon.id),
                "type": "configured-link-addons",
                "attributes": {"target_id": None, "resource_type": None},
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
        self.assertEqual(
            self._addon.int_resource_type, SupportedResourceTypes.Other.value
        )

    def test_create_with_null_values(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            authorized_resource=self._resource,
            base_account=self._authorized_account,
            target_id=None,
            int_resource_type=None,
        )

        addon.int_resource_type = None
        addon.save(full_clean=False)

        addon.refresh_from_db()
        self.assertIsNone(addon.target_id)

        self.assertIsNone(addon.int_resource_type)
        self.assertIsNone(addon.resource_type)
