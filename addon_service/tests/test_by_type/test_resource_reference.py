import json
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.resource_reference.views import ResourceReferenceViewSet
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    get_test_request,
    MockOSF,
    with_mocked_httpx_get,
)
from app import settings


class TestResourceReferenceAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._resource = cls._csa.authorized_resource
        # _user magically becomes the current requester
        cls._user = cls._csa.base_account.external_account.owner

    def setUp(self):
        super().setUp()
        self.client.cookies[settings.USER_REFERENCE_COOKIE] = self._user.user_uri
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(user_uri=self._user.user_uri, resource_uri=self._resource.resource_uri, role='admin')
        self.enterContext(self._mock_osf)

    @property
    def _detail_path(self):
        return reverse("resource-references-detail", kwargs={"pk": self._resource.pk})

    @property
    def _list_path(self):
        return reverse("resource-references-list")

    @property
    def _related_configured_storage_addons_path(self):
        return reverse(
            "resource-references-related",
            kwargs={
                "pk": self._resource.pk,
                "related_field": "configured_storage_addons",
            },
        )

    def test_get(self):
        _resp = self.client.get(self._detail_path)
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data["resource_uri"], self._resource.resource_uri)

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._detail_path: {"patch", "put", "post"},
            self._related_configured_storage_addons_path: {"patch", "put", "post"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


# unit-test data model
class TestResourceReferenceModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._resource = _factories.ResourceReferenceFactory()

    def test_can_load(self):
        _resource_from_db = db.ResourceReference.objects.get(id=self._resource.id)
        self.assertEqual(self._resource.resource_uri, _resource_from_db.resource_uri)

    def test_configured_storage_addons__empty(self):
        self.assertEqual(
            list(self._resource.configured_storage_addons.all()),
            [],
        )

    def test_configured_storage_addons__several(self):
        _accounts = set(
            _factories.ConfiguredStorageAddonFactory.create_batch(
                size=3,
                authorized_resource=self._resource,
            )
        )
        self.assertEqual(
            set(self._resource.configured_storage_addons.all()),
            _accounts,
        )

    def test_validation(self):
        self._resource.resource_uri = "not a uri"
        with self.assertRaises(ValidationError):
            self._resource.clean_fields(exclude=["modified"])


# unit-test viewset (call the view with test requests)
class TestResourceReferenceViewSet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._view = ResourceReferenceViewSet.as_view({"get": "retrieve"})
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._resource = cls._csa.authorized_resource
        # _user magically becomes the current requester
        cls._user = cls._csa.base_account.external_account.owner

    def setUp(self):
        self._mock_osf = MockOSF()
        self._mock_osf.configure_user_role(self._user.user_uri, self._resource.resource_uri, 'admin')
        self.enterContext(self._mock_osf)

    def test_get(self):
        _resp = self._view(
            get_test_request(cookies={"osf": self._user.user_uri}),
            pk=self._resource.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            set(_content["data"]["attributes"].keys()),
            {
                "resource_uri",
            },
        )
        self.assertEqual(
            set(_content["data"]["relationships"].keys()),
            {
                "configured_storage_addons",
            },
        )

    def test_unauthorized__private_resource(self):
        self._mock_osf.configure_resource_visibility(self._resource.resource_uri, public=False)
        _anon_resp = self._view(get_test_request(), pk=self._resource.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.FORBIDDEN)

    def test_unauthorized__public_resource(self):
        self._mock_osf.configure_resource_visibility(self._resource.resource_uri, public=True)
        _anon_resp = self._view(get_test_request(), pk=self._resource.pk)
        self.assertEqual(_anon_resp.status_code, HTTPStatus.OK)

    def test_wrong_user__pivate_resource(self):
        self._mock_osf.configure_resource_visibility(self._resource.resource_uri, public=False)
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: "this is wrong user auth"}
            ),
            pk=self._resource.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.FORBIDDEN)

    def test_wrong_user__public_resource(self):
        self._mock_osf.configure_resource_visibility(self._resource.resource_uri, public=True)
        _resp = self._view(
            get_test_request(
                cookies={settings.USER_REFERENCE_COOKIE: "this is wrong user auth"}
            ),
            pk=self._resource.pk,
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)


class TestResourceReferenceRelatedView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._resource = _factories.ResourceReferenceFactory()
        cls._related_view = ResourceReferenceViewSet.as_view(
            {"get": "retrieve_related"},
        )
        cls._csa = _factories.ConfiguredStorageAddonFactory()
        cls._resource = cls._csa.authorized_resource
        # _user magically becomes the current requester
        cls._user = cls._csa.base_account.external_account.owner

    @with_mocked_httpx_get
    def test_get_related__empty(self):
        self._csa.delete()

        _resp = self._related_view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._resource.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        self.assertEqual(_resp.data, [])

    @with_mocked_httpx_get
    def test_get_related__several(self):
        _addons = _factories.ConfiguredStorageAddonFactory.create_batch(
            size=4,
            authorized_resource=self._resource,
        ) + [self._csa]
        _resp = self._related_view(
            get_test_request(cookies={"osf": "This is my chosen form of auth"}),
            pk=self._resource.pk,
            related_field="configured_storage_addons",
        )
        self.assertEqual(_resp.status_code, HTTPStatus.OK)
        _content = json.loads(_resp.rendered_content)
        self.assertEqual(
            {_datum["id"] for _datum in _content["data"]},
            {str(_addon.pk) for _addon in _addons},
        )
