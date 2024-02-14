import base64
import json
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.configured_storage_addon.views import ConfiguredStorageAddonViewSet
from addon_service.resource_reference.models import ResourceReference
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    get_test_request,
    with_mocked_httpx_get,
    with_mocked_httpx_get_403,
)
from app import settings


class TestConfiguredStorageAddonAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._user = cls._csa.base_account.external_account.owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = [
            "Some form of auth is necessary or POSTS are ignored."
        ]

    @property
    def _detail_path(self):
        return reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._csa.pk},
        )

    @property
    def _list_path(self):
        return reverse("configured-storage-addons-list")

    def _related_path(self, related_field):
        return reverse(
            "configured-storage-addons-related",
            kwargs={
                "pk": self._csa.pk,
                "related_field": related_field,
            },
        )

    @with_mocked_httpx_get
    def test_get_detail(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            _resp.data["root_folder"],
            self._csa.root_folder,
        )

    @with_mocked_httpx_get
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
class TestConfiguredStorageAddonModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()

    def test_can_load(self):
        _resource_from_db = db.ConfiguredStorageAddon.objects.get(id=self._csa.id)
        self.assertEqual(self._csa.pk, _resource_from_db.pk)


# unit-test viewset (call the view with test requests)
class TestConfiguredStorageAddonViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._view = ConfiguredStorageAddonViewSet.as_view(
            {
                "post": "create",
                "get": "retrieve",
                "patch": "update",
            }
        )
        cls._user = cls._csa.base_account.external_account.owner

    @with_mocked_httpx_get
    def test_get(self):
        _resp = self._view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._csa.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "root_folder",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "base_account",
                "authorized_resource",
            },
        )

    @with_mocked_httpx_get
    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._csa.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    @with_mocked_httpx_get_403
    def test_wrong_user(self):
        _resp = self._view(
            get_test_request(cookies={"osf": "This is invalid auth"}),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestConfiguredStorageAddonRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._related_view = ConfiguredStorageAddonViewSet.as_view(
            {"get": "retrieve_related"},
        )
        cls._user = cls._csa.base_account.external_account.owner

    @with_mocked_httpx_get
    def test_get_related(self):
        _resp = self._related_view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._csa.pk,
            related_field="base_account",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            _content["data"]["id"],
            str(self._csa.base_account_id),
        )


class ConfiguredStorageAddonPOSTAPIBase:
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = (
            cls._asa.external_account.owner
        )  # so we know whose details to expect in mock response
        cls.default_payload = {
            "data": {
                "type": "configured-storage-addons",
                "relationships": {
                    "base_account": {
                        "data": {
                            "type": "authorized-storage-accounts",
                            "id": cls._asa.id,
                        }
                    },
                    "authorized_resource": {
                        "data": {
                            "type": "resource-references",
                            "id": "http://domain.com/test0/",
                        }
                    },
                },
            }
        }

    @with_mocked_httpx_get
    def test_post_without_resource(self):
        """
        Test for request made without an InternalResource in the system, so
        one must be created
        """
        assert not self._asa.configured_storage_addons.exists()

        response = self.client.post(
            reverse("configured-storage-addons-list"),
            self.default_payload,
            format="vnd.api+json",
        )
        self.assertEqual(response.status_code, 201)
        configured_storage_addon = self._asa.configured_storage_addons.first()
        assert configured_storage_addon
        assert configured_storage_addon.authorized_resource

    @with_mocked_httpx_get
    def test_post_with_resource(self):
        """
        Test for request made with a pre-existing ResourceReference in the system, don't create one.
        """
        assert not self._asa.configured_storage_addons.exists()  # sanity/factory check
        resource = _factories.ResourceReferenceFactory()
        self.default_payload["data"]["relationships"]["authorized_resource"]["data"][
            "id"
        ] = resource.resource_uri

        response = self.client.post(
            reverse("configured-storage-addons-list"),
            self.default_payload,
            format="vnd.api+json",
        )
        self.assertEqual(response.status_code, 201)
        configured_storage_addon = self._asa.configured_storage_addons.first()
        assert configured_storage_addon
        assert (
            configured_storage_addon.authorized_resource.resource_uri
            == resource.resource_uri
        )
        assert ResourceReference.objects.all().count() == 1


class TestConfiguredStorageAddonPOSTAPISession(
    ConfiguredStorageAddonPOSTAPIBase, APITestCase
):
    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = [
            "Some form of auth is necessary or POSTS are ignored."
        ]


class TestConfiguredStorageAddonPOSTAPIOauth(
    ConfiguredStorageAddonPOSTAPIBase, APITestCase
):
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer valid_token")


class TestConfiguredStorageAddonPOSTAPIBasic(
    ConfiguredStorageAddonPOSTAPIBase, APITestCase
):
    def setUp(self):
        super().setUp()
        credentials = base64.b64encode("admin:password".encode()).decode()
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")


class TestConfiguredStorageAddonPOSTAPINoAuth(
    ConfiguredStorageAddonPOSTAPIBase, APITestCase
):
    @with_mocked_httpx_get
    def test_post_without_resource(self):
        """
        Test for request made without an InternalResource in the system, so
        one must be created
        """
        assert not self._asa.configured_storage_addons.exists()

        response = self.client.post(
            reverse("configured-storage-addons-list"),
            self.default_payload,
            format="vnd.api+json",
        )
        self.assertEqual(response.status_code, 401)

    @with_mocked_httpx_get
    def test_post_with_resource(self):
        """
        Test for request made with a pre-existing InternalResource
        in the system, don't create one.
        """
        resource = _factories.ResourceReferenceFactory()
        assert not self._asa.configured_storage_addons.exists()  # sanity/factory check

        self.default_payload["data"]["relationships"]["authorized_resource"]["data"][
            "id"
        ] = resource.resource_uri

        response = self.client.post(
            reverse("configured-storage-addons-list"),
            self.default_payload,
            format="vnd.api+json",
        )
        self.assertEqual(response.status_code, 401)
