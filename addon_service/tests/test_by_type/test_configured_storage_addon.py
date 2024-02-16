import base64
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.models import ConfiguredStorageAddon
from addon_service.tests import _factories as test_factories
from addon_service.tests._helpers import with_mocked_httpx_get
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
        cls.configured_storage_addon = test_factories.ConfiguredStorageAddonFactory()
        cls.user = cls.configured_storage_addon.base_account.external_account.owner

    def detail_url(self):
        return reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self.configured_storage_addon.pk},
        )

    def list_url(self):
        return reverse("configured-storage-addons-list")

    def related_url(self, related_field):
        return reverse(
            "configured-storage-addons-related",
            kwargs={
                "pk": self.configured_storage_addon.pk,
                "related_field": related_field,
            },
        )


class ConfiguredStorageAddonAPITests(BaseAPITest):
    @with_mocked_httpx_get
    def test_get_detail(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json()["root_folder"], self.configured_storage_addon.root_folder
        )

    @with_mocked_httpx_get
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
        cls.configured_storage_addon = test_factories.ConfiguredStorageAddonFactory()

    def test_model_loading(self):
        loaded_addon = ConfiguredStorageAddon.objects.get(
            id=self.configured_storage_addon.id
        )
        self.assertEqual(self.configured_storage_addon.pk, loaded_addon.pk)


class ConfiguredStorageAddonViewSetTests(BaseAPITest):
    @with_mocked_httpx_get
    def test_viewset_retrieve(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @with_mocked_httpx_get(response_status=403)
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
                "authorized_resource": {
                    "data": {"type": "resource-references", "id": ""}
                },
            },
        }
    }

    def setUp(self):
        super().setUp()
        self.default_payload["data"]["relationships"]["base_account"]["data"][
            "id"
        ] = str(self.configured_storage_addon.base_account_id)

    @with_mocked_httpx_get
    def test_post_with_new_resource(self):
        self.assertFalse(ConfiguredStorageAddon.objects.exists())
        new_resource_uri = "http://example.com/new_resource/"
        self.default_payload["data"]["relationships"]["authorized_resource"]["data"][
            "id"
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

    def test_post_various_auth_methods(self):
        for auth_type in ["oauth", "basic", "no_auth", "session"]:
            with self.subTest(auth_type=auth_type):
                self.set_auth_header(auth_type)
                self.test_post_with_new_resource()
