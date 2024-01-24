import json
import unittest
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.configured_storage_addon.views import ConfiguredStorageAddonViewSet
from addon_service.tests import _factories
from addon_service.tests._helpers import get_test_request


class TestConfiguredStorageAddonAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()

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

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(
            _resp.data["root_folder"],
            self._csa.root_folder,
        )

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"post"},
            # TODO: self._list_path: {'get', 'patch', 'put', 'post'},
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

    def test_get(self):
        _resp = self._view(
            get_test_request(),
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

    @unittest.expectedFailure  # TODO
    def test_unauthorized(self):
        _anon_resp = self._view(get_test_request(), pk=self._user.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.UNAUTHORIZED)

    @unittest.expectedFailure  # TODO
    def test_wrong_user(self):
        _another_user = _factories.InternalUserFactory()
        _resp = self._view(
            get_test_request(user=_another_user),
            pk=self._user.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)

    # def test_create(self):
    #     _post_req = get_test_request(user=self._user, method='post')
    #     self._view(_post_req, pk=


class TestConfiguredStorageAddonRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._related_view = ConfiguredStorageAddonViewSet.as_view(
            {"get": "retrieve_related"},
        )

    def test_get_related(self):
        _resp = self._related_view(
            get_test_request(),
            pk=self._csa.pk,
            related_field="base_account",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            _content["data"]["id"],
            str(self._csa.base_account_id),
        )


class TestConfiguredStorageAddonPOSTAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._asa = _factories.AuthorizedStorageAccountFactory()

    def test_post(self):
        assert not self._asa.configured_storage_addons.all()  # sanity/factory check

        payload = {
            "data": {
                "type": "configured-storage-addons",
                "attributes": {
                    "guid": "<placeholder-guid>",
                },
                "relationships": {
                    "base_account": {
                        "data": {
                            "type": "authorized-storage-accounts",
                            "id": self._asa.id,
                        }
                    },
                },
            }
        }

        response = self.client.post(
            reverse("configured-storage-addons-list"), payload, format="vnd.api+json"
        )
        self.assertEqual(response.status_code, 201)
        assert self._asa.configured_storage_addons.all()
