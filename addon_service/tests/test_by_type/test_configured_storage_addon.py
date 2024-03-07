import base64
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.models import (
    ConfiguredStorageAddon,
    ResourceReference,
)
from addon_service.tests import _factories as test_factories
from addon_service.tests._helpers import MockOSF
from app import settings


class BaseAPITest(APITestCase):
    def set_auth_header(self, auth_type):
        if auth_type == "oauth":
            self.client.credentials(HTTP_AUTHORIZATION="Bearer valid_token")
        elif auth_type == "basic":
            credentials = base64.b64encode(b"admin:password").decode()
            self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")
        elif auth_type == "session":
            self.client.cookies[settings.USER_REFERENCE_COOKIE] = "some auth"
        elif auth_type == "no_auth":
            self.client.cookies.clear()
            self.client.credentials()

    @classmethod
    def setUpTestData(cls):
        cls._configured_storage_addon = test_factories.ConfiguredStorageAddonFactory()
        cls._user = cls._configured_storage_addon.base_account.external_account.owner

    def setUp(self):
        self._mock_osf = MockOSF()
        self.addCleanup(self._mock_osf.stop)
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._configured_storage_addon.resource_uri, "admin"
        )
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri

    def detail_url(self):
        return reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._configured_storage_addon.pk},
        )

    def list_url(self):
        return reverse("configured-storage-addons-list")

    def related_url(self, related_field):
        return reverse(
            "configured-storage-addons-related",
            kwargs={
                "pk": self._configured_storage_addon.pk,
                "related_field": related_field,
            },
        )


class ConfiguredStorageAddonAPITests(BaseAPITest):
    def test_get_detail(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json()["data"]["attributes"]["root_folder"],
            self._configured_storage_addon.root_folder,
        )

    def test_methods_not_allowed(self):
        not_allowed_methods = {
            self.detail_url(): ["post"],
            self.list_url(): ["patch", "put", "get"],
            self.related_url("account_owner"): ["patch", "put", "post"],
        }
        for url, methods in not_allowed_methods.items():
            for method in methods:
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class ConfiguredStorageAddonModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._configured_storage_addon = test_factories.ConfiguredStorageAddonFactory()

    def test_model_loading(self):
        loaded_addon = ConfiguredStorageAddon.objects.get(
            id=self._configured_storage_addon.id
        )
        self.assertEqual(self._configured_storage_addon.pk, loaded_addon.pk)


class ConfiguredStorageAddonViewSetTests(BaseAPITest):
    def test_viewset_retrieve(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauthorized_user(self):
        self.set_auth_header("session")
        response = self.client.get(self.related_url("base_account"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class ConfiguredStorageAddonPOSTTests(BaseAPITest):
    default_payload = {
        "data": {
            "type": "configured-storage-addons",
            "relationships": {
                "base_account": {
                    "data": {"type": "authorized-storage-accounts", "id": ""}
                },
                "authorized_resource": {"data": {"type": "resource-references"}},
            },
        }
    }

    def setUp(self):
        super().setUp()
        self.default_payload["data"]["relationships"]["base_account"]["data"][
            "id"
        ] = self._configured_storage_addon.base_account_id

    def test_post_with_new_resource(self):
        new_resource_uri = "http://example.com/new_resource/"
        self._mock_osf.configure_user_role(
            self._user.user_uri, new_resource_uri, "admin"
        )
        self.assertFalse(
            ResourceReference.objects.filter(resource_uri=new_resource_uri).exists()
        )
        self.default_payload["data"]["relationships"]["authorized_resource"]["data"][
            "resource_uri"
        ] = new_resource_uri

        response = self.client.post(
            self.list_url(), self.default_payload, format="vnd.api+json"
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(
            ConfiguredStorageAddon.objects.filter(
                authorized_resource__resource_uri=new_resource_uri
            ).exists()
        )
