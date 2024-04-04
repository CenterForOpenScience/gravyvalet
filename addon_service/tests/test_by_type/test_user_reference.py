import json
from http import HTTPStatus

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    get_test_request,
)
from addon_service.user_reference.views import UserReferenceViewSet


class TestUserReferenceAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

    @property
    def _detail_path(self):
        return reverse("user-references-detail", kwargs={"pk": self._user.pk})

    @property
    def _list_path(self):
        return reverse("user-references-list")

    @property
    def _related_accounts_path(self):
        return reverse(
            "user-references-related",
            kwargs={
                "pk": self._user.pk,
                "related_field": "authorized_storage_accounts",
            },
        )

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "user_uri",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "authorized_storage_accounts",
            },
        )

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"patch", "put", "post"},
            self._related_accounts_path: {"patch", "put", "post"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


# unit-test data model
class TestUserReferenceModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()

    def test_can_load(self):
        _user_from_db = db.UserReference.objects.get(id=self._user.id)
        self.assertEqual(self._user.user_uri, _user_from_db.user_uri)

    def test_authorized_storage_accounts__empty(self):
        _authed_storage_accounts_qs = self._user.authorized_storage_accounts
        self.assertIsInstance(_authed_storage_accounts_qs, QuerySet)
        self.assertEqual(list(_authed_storage_accounts_qs), [])

    def test_authorized_storage_accounts__several(self):
        _accounts = set(
            _factories.AuthorizedStorageAccountFactory.create_batch(
                size=3,
                external_account__owner=self._user,
            )
        )
        _authed_storage_accounts_qs = self._user.authorized_storage_accounts
        self.assertIsInstance(_authed_storage_accounts_qs, QuerySet)
        self.assertEqual(set(_authed_storage_accounts_qs), _accounts)

    def test_validation(self):
        self._user.user_uri = "not a uri"
        with self.assertRaises(ValidationError):
            self._user.clean_fields(exclude=["modified"])

    def test_deactivate(self):
        self.assertIsNone(self._user.deactivated)
        self._user.deactivate()
        self.assertIsNotNone(self._user.deactivated)

    def test_delete(self):
        with self.assertRaises(NotImplementedError):
            self._user.delete()

    def test_reactivate(self):
        self._user.deactivate()
        self.assertIsNotNone(self._user.deactivated)
        self._user.reactivate()
        self.assertIsNone(self._user.deactivated)

    def test_merge(self):
        merge_with = _factories.UserReferenceFactory()
        _accounts_before_merge = self._user.configured_storage_addons.count()
        self._user.merge(merge_with)
        _accounts_after_merge = self._user.configured_storage_addons.count()
        self.assertEqual(
            _accounts_after_merge,
            _accounts_before_merge + merge_with.configured_storage_addons.count(),
        )


# unit-test viewset (call the view with test requests)
class TestUserReferenceViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._view = UserReferenceViewSet.as_view({"get": "retrieve"})

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())

    def test_get(self):
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: self._user.user_uri},
            ),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "user_uri",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "authorized_storage_accounts",
            },
        )

    def test_wrong_user(self):
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: "this is the wrong cookie"}
            ),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)

    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._user.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)


class TestUserReferenceRelatedView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._related_view = UserReferenceViewSet.as_view({"get": "retrieve_related"})

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self.enterContext(self._mock_osf.mocking())
        self.request = get_test_request(
            user=self._user,
            cookies={settings.USER_REFERENCE_COOKIE: self._user.user_uri},
        )

    def test_get_related__empty(self):
        _resp = self._related_view(
            self.request,
            pk=self._user.pk,
            related_field="authorized_storage_accounts",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    def test_get_related__several(self):
        _accounts = _factories.AuthorizedStorageAccountFactory.create_batch(
            size=5,
            external_account__owner=self._user,
        )
        _resp = self._related_view(
            self.request,
            pk=self._user.pk,
            related_field="authorized_storage_accounts",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_account.pk) for _account in _accounts},
        )
