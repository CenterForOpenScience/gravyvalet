import base64
from http import HTTPStatus

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from addon_service.common import hmac as hmac_utils
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.models import (
    ConfiguredStorageAddon,
    ResourceReference,
)
from addon_service.tests import _factories as test_factories
from addon_service.tests._helpers import MockOSF
from addon_toolkit.credentials import AccessTokenCredentials


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
        cls._user = cls._configured_storage_addon.base_account.account_owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._configured_storage_addon.resource_uri, "admin"
        )
        self.enterContext(self._mock_osf.mocking())

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
            response.data["root_folder"],
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
        # Create active and deactivated users via your factory setup or directly
        cls.active_user = test_factories.UserReferenceFactory(
            deactivated=None
        )  # Assuming you have a factory for UserReference
        cls.disabled_user = test_factories.UserReferenceFactory(
            deactivated=timezone.now()
        )

        cls.active_configured_storage_addon = (
            test_factories.ConfiguredStorageAddonFactory(account_owner=cls.active_user)
        )
        cls.disabled_configured_storage_addon = (
            test_factories.ConfiguredStorageAddonFactory(
                account_owner=cls.disabled_user
            )
        )

    def test_model_loading(self):
        loaded_addon = ConfiguredStorageAddon.objects.get(
            id=self.active_configured_storage_addon.id
        )
        self.assertEqual(self.active_configured_storage_addon.pk, loaded_addon.pk)

    def test_active_user_manager_excludes_disabled_users(self):
        # Fetch all configured storage addons using the manager
        addons = ConfiguredStorageAddon.objects.active()

        # Ensure that only addons associated with active users are returned
        self.assertIn(self.active_configured_storage_addon, addons)
        self.assertNotIn(self.disabled_configured_storage_addon, addons)


class ConfiguredStorageAddonViewSetTests(BaseAPITest):
    def test_viewset_retrieve(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauthorized_user(self):
        self.set_auth_header("session")
        response = self.client.get(self.related_url("base_account"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class ConfiguredStorageAddonPOSTTests(BaseAPITest):
    def get_payload(self, resource_uri: str) -> dict:
        return {
            "data": {
                "type": "configured-storage-addons",
                "attributes": {
                    "display_name": "this display name",
                    "connected_capabilities": ["ACCESS"],
                    "authorized_resource_uri": resource_uri,
                },
                "relationships": {
                    "base_account": {
                        "data": {
                            "type": "authorized-storage-accounts",
                            "id": self._configured_storage_addon.base_account.pk,
                        },
                    },
                },
            }
        }

    def test_post_with_new_resource(self):
        new_resource_uri = "http://example.com/new_resource/"
        self._mock_osf.configure_user_role(
            self._user.user_uri, new_resource_uri, "admin"
        )
        self.assertFalse(
            ResourceReference.objects.filter(resource_uri=new_resource_uri).exists()
        )

        response = self.client.post(
            self.list_url(),
            self.get_payload(
                new_resource_uri,
            ),
            format="vnd.api+json",
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        _created = ConfiguredStorageAddon.objects.get(pk=response.data["id"])
        self.assertEqual(_created.resource_uri, new_resource_uri)
        self.assertEqual(_created.display_name, "this display name")


class TestWBConfigRetrieval(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls._configured_storage_addon = test_factories.ConfiguredStorageAddonFactory(
            credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN,
            credentials=AccessTokenCredentials(access_token="access"),
        )
        cls._user = cls._configured_storage_addon.account_owner
        cls._external_service = cls._configured_storage_addon.external_service

    def test_get_waterbutler_credentials(self):
        request_url = reverse(
            "configured-storage-addons-waterbutler-credentials",
            kwargs={
                "pk": self._configured_storage_addon.pk,
            },
        )
        response = self.client.get(
            request_url,
            headers=hmac_utils.make_signed_headers(
                request_url=request_url,
                request_method="GET",
                hmac_key=settings.OSF_HMAC_KEY,
            ),
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["data"]["type"], "waterbutler-credentials")

        self.assertEqual(response.data["credentials"], {"token": "access"})

    def test_get_waterbutler_credentials__error__no_headers(self):
        # credentials request requires HMAC-signed headers
        # Cookie + OSF-side permissions will not suffice
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = "some auth"
        _mock_osf = MockOSF()
        _mock_osf.configure_user_role(
            self._user.user_uri, self._configured_storage_addon.resource_uri, "admin"
        )
        request_url = reverse(
            "configured-storage-addons-waterbutler-credentials",
            kwargs={
                "pk": self._configured_storage_addon.pk,
            },
        )
        with _mock_osf.mocking():
            response = self.client.get(
                request_url,
            )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
