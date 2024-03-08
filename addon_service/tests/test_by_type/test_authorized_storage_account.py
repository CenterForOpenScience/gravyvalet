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
    MockOSF
)
from app import settings


class TestAuthorizedStorageAccountAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()
        cls._user = cls._asa.account_owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf)

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

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            _resp.data["default_root_folder"],
            self._asa.default_root_folder,
        )

    def test_post(self):
        external_service = _factories.ExternalStorageServiceFactory()
        self.assertFalse(external_service.authorized_storage_accounts.exists())
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
                            "id": external_service.id,
                        }
                    },
                },
            }
        }

        _resp = self.client.post(
            reverse("authorized-storage-accounts-list"), payload, format="vnd.api+json"
        )
        self.assertEqual(_resp.status_code, 201)
        created_account_id = int(_resp.data['url'].rstrip('/').split('/')[-1])
        self.assertTrue(external_service.authorized_storage_accounts.filter(id=created_account_id).exists())

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


    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf)

    def test_get(self):
        _resp = self._view(
            get_test_request(cookies={"osf": self._user.user_uri}),
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
        _anon_resp = self._view(get_test_request(), pk=self._asa.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    def test_wrong_user(self):
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: "wrong/10"}
            ),
            pk=self._asa.pk,
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

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf)

    def test_get_related__empty(self):
        _resp = self._related_view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    def test_get_related__several(self):
        _addons = _factories.ConfiguredStorageAddonFactory.create_batch(
            size=5,
            base_account=self._asa,
        )
        _resp = self._related_view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._asa.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_addon.pk) for _addon in _addons},
        )
