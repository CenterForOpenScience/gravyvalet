import json
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.authorized_storage_account.views import (
    AuthorizedStorageAccountViewSet,
)
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    get_test_request,
    with_mocked_httpx_get,
)
from app import settings


class TestAuthorizedStorageAccountAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.external_account.owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = [
            "Some form of auth is necessary or POSTS are ignored."
        ]

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

    @with_mocked_httpx_get
    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            _resp.data["default_root_folder"],
            self._asa.default_root_folder,
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
class TestAuthorizedStorageAccountModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()

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


# unit-test viewset (call the view with test requests)
class TestAuthorizedStorageAccountViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.external_account.owner
        cls._view = AuthorizedStorageAccountViewSet.as_view({"get": "retrieve"})

    @with_mocked_httpx_get
    def test_get(self):
        _resp = self._view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._asa.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "default_root_folder",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "account_owner",
                "external_storage_service",
                "configured_storage_addons",
            },
        )

    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._user.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    @with_mocked_httpx_get(response_status=403)
    def test_wrong_user(self):
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: "this is wrong user auth"}
            ),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestAuthorizedStorageAccountRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.external_account.owner
        cls._related_view = AuthorizedStorageAccountViewSet.as_view(
            {"get": "retrieve_related"},
        )

    @with_mocked_httpx_get
    def test_get_related__empty(self):
        _resp = self._related_view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    @with_mocked_httpx_get
    def test_get_related__several(self):
        _addons = _factories.ConfiguredStorageAddonFactory.create_batch(
            size=5,
            base_account=self._asa,
        )
        _resp = self._related_view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_addon.pk) for _addon in _addons},
        )


class TestAuthorizedStorageAccountPOSTAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ess = _factories.ExternalStorageServiceFactory()
        cls._ea = _factories.ExternalAccountFactory()
        cls._user = cls._ea.owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = [
            "Some form of auth is necessary or POSTS are ignored."
        ]

    @with_mocked_httpx_get
    def test_post(self):
        assert not self._ess.authorized_storage_accounts.all()  # sanity/factory check

        payload = {
            "data": {
                "type": "authorized-storage-accounts",
                "attributes": {
                    "username": "<placeholder-username>",
                    "password": "<placeholder-password>",
                },
                "relationships": {
                    "external_storage_service": {
                        "data": {
                            "type": "external-storage-services",
                            "id": self._ess.auth_uri,
                        }
                    },
                    "account_owner": {
                        "data": {
                            "id": self._user.user_uri,
                            "type": "user-references",
                        }
                    },
                },
            }
        }

        response = self.client.post(
            reverse("authorized-storage-accounts-list"), payload, format="vnd.api+json"
        )
        self.assertEqual(response.status_code, 201)
        assert self._ess.authorized_storage_accounts.all()
