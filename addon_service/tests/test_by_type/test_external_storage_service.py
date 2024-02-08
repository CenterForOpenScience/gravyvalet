import json
import unittest
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.external_storage_service.views import ExternalStorageServiceViewSet
from addon_service.tests import _factories
from addon_service.tests._helpers import get_test_request


class TestExternalStorageServiceAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ess = _factories.ExternalStorageServiceFactory()

    @property
    def _detail_path(self):
        return reverse("external-storage-services-detail", kwargs={"pk": self._ess.pk})

    @property
    def _list_path(self):
        return reverse("external-storage-services-list")

    @property
    def _related_authorized_storage_accounts_path(self):
        return reverse(
            "external-storage-services-related",
            kwargs={
                "pk": self._ess.pk,
                "related_field": "authorized_storage_accounts",
            },
        )

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["auth_uri"], self._ess.auth_uri)

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"post"},
            # TODO: self._list_path: {'get', 'patch', 'put', 'post'},
            self._related_authorized_storage_accounts_path: {"patch", "put", "post"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


# unit-test data model
class TestExternalStorageServiceModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ess = _factories.ExternalStorageServiceFactory()

    def test_can_load(self):
        _resource_from_db = db.ExternalStorageService.objects.get(id=self._ess.id)
        self.assertEqual(self._ess.auth_uri, _resource_from_db.auth_uri)

    def test_authorized_storage_accounts__empty(self):
        self.assertEqual(
            list(self._ess.authorized_storage_accounts.all()),
            [],
        )

    def test_authorized_storage_accounts__several(self):
        _accounts = set(
            _factories.AuthorizedStorageAccountFactory.create_batch(
                size=3,
                external_storage_service=self._ess,
            )
        )
        self.assertEqual(
            set(self._ess.authorized_storage_accounts.all()),
            _accounts,
        )

    def test_validation(self):
        self._ess.auth_uri = "not a uri"
        with self.assertRaises(ValidationError):
            self._ess.clean_fields(exclude=["modified"])


# unit-test viewset (call the view with test requests)
class TestExternalStorageServiceViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ess = _factories.ExternalStorageServiceFactory()
        cls._view = ExternalStorageServiceViewSet.as_view({"get": "retrieve"})

    def test_get(self):
        _resp = self._view(
            get_test_request(),
            pk=self._ess.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "auth_uri",
                "max_concurrent_downloads",
                "max_upload_mb",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "authorized_storage_accounts",
            },
        )

    @unittest.expectedFailure  # TODO
    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._user.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    @unittest.expectedFailure  # TODO
    def test_wrong_user(self):
        _another_user = _factories.UserReferenceFactory()
        _resp = self._view(
            get_test_request(user=_another_user),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)


class TestExternalStorageServiceRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._ess = _factories.ExternalStorageServiceFactory()
        cls._related_view = ExternalStorageServiceViewSet.as_view(
            {"get": "retrieve_related"},
        )

    def test_get_related__empty(self):
        _resp = self._related_view(
            get_test_request(),
            pk=self._ess.pk,
            related_field="authorized_storage_accounts",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    def test_get_related__several(self):
        _accounts = _factories.AuthorizedStorageAccountFactory.create_batch(
            size=5,
            external_storage_service=self._ess,
        )
        _resp = self._related_view(
            get_test_request(),
            pk=self._ess.pk,
            related_field="authorized_storage_accounts",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_account.pk) for _account in _accounts},
        )
