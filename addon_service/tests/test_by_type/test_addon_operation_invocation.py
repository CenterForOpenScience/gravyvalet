import dataclasses
import json
import typing
from http import HTTPStatus

from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.common.aiohttp_session import close_aiohttp_client_session_sync
from addon_service.common.invocation import InvocationStatus
from addon_service.tests import _factories
from addon_service.tests._helpers import (
    MockOSF,
    jsonapi_ref,
)


@dataclasses.dataclass
class _InvocationCase:
    operation_name: str
    operation_kwargs: dict
    expected_http_status: HTTPStatus = HTTPStatus.CREATED
    expected_invocation_status: InvocationStatus = InvocationStatus.SUCCESS
    expected_result: typing.Any = None


class TestAddonOperationInvocationCreate(APITestCase):
    _INVOKE_SUCCESS_CASES = (
        _InvocationCase(
            "get_root_items",
            {},
            expected_result={
                "items": [
                    {
                        "item_id": "hello",
                        "item_name": "Hello!?",
                        "item_type": "FOLDER",
                    }
                ],
                "total_count": 1,
                "this_sample_cursor": "",
                "first_sample_cursor": "",
            },
        ),
    )
    _INVOKE_PROBLEM_CASES = (
        _InvocationCase(
            "get_root_items",
            {"blarg": 2},
            expected_http_status=HTTPStatus.BAD_REQUEST,
        ),
    )

    @classmethod
    def setUpTestData(cls):
        cls._configured_addon = _factories.ConfiguredStorageAddonFactory()

    def setUp(self):
        super().setUp()
        self.addCleanup(close_aiohttp_client_session_sync)
        self._mock_osf = MockOSF({self._resource_uri: {self._user_uri: "admin"}})
        self._mock_osf.configure_assumed_caller(self._user_uri)
        self.enterContext(self._mock_osf.mocking())

    @property
    def _resource_uri(self):
        return self._configured_addon.resource_uri

    @property
    def _user_uri(self):
        return self._configured_addon.owner_uri

    @property
    def _invocation_list_path(self):
        return reverse("addon-operation-invocations-list")

    def _invocation_post_payload(self, case: _InvocationCase):
        return {
            "data": {
                "type": "addon-operation-invocations",
                "attributes": {
                    "operation_kwargs": case.operation_kwargs,
                    "operation_name": case.operation_name,
                },
                "relationships": {
                    "thru_addon": {
                        "data": jsonapi_ref(self._configured_addon),
                    },
                },
            }
        }

    def test_immediate_success(self):
        for _inv_case in self._INVOKE_SUCCESS_CASES:
            with self.subTest(_inv_case):
                _resp = self.client.post(
                    self._invocation_list_path,
                    data=json.dumps(self._invocation_post_payload(_inv_case)),
                    content_type="application/vnd.api+json",
                )
                with self.subTest("expected http status"):
                    self.assertEqual(_resp.status_code, _inv_case.expected_http_status)
                with self.subTest("expected invocation status"):
                    self.assertEqual(
                        _resp.data["invocation_status"],
                        _inv_case.expected_invocation_status.name,
                    )
                with self.subTest("expected operation result"):
                    self.assertEqual(
                        _resp.data["operation_result"], _inv_case.expected_result
                    )

    def test_immediate_problem(self):
        for _inv_case in self._INVOKE_PROBLEM_CASES:
            with self.subTest(_inv_case):
                _resp = self.client.post(
                    self._invocation_list_path,
                    data=json.dumps(self._invocation_post_payload(_inv_case)),
                    content_type="application/vnd.api+json",
                )
                with self.subTest("expected http status"):
                    self.assertEqual(_resp.status_code, _inv_case.expected_http_status)
                if _inv_case.expected_http_status.is_success:
                    with self.subTest("expected invocation status"):
                        self.assertEqual(
                            _resp.data["invocation_status"],
                            _inv_case.expected_invocation_status.name,
                        )
                    with self.subTest("expected operation result"):
                        self.assertEqual(
                            _resp.data["operation_result"], _inv_case.expected_result
                        )


class TestAddonOperationInvocationErrors(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._invocation = _factories.AddonOperationInvocationFactory()

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._invocation.by_user.user_uri)
        self.enterContext(self._mock_osf.mocking())

    @property
    def _detail_path(self):
        return reverse(
            "addon-operation-invocations-detail",
            kwargs={"pk": self._invocation.pk},
        )

    @property
    def _invocation_list_path(self):
        return reverse("addon-operation-invocations-list")

    def _related_path(self, related_field):
        return reverse(
            "addon-operation-invocations-related",
            kwargs={
                "pk": self._invocation.pk,
                "related_field": related_field,
            },
        )

    def test_methods_not_allowed(self):
        _methods_not_allowed = {
            self._invocation_list_path: {"get", "patch", "put"},
            self._detail_path: {"put", "post", "delete"},
            self._related_path("thru_addon"): {"patch", "put", "post", "delete"},
            self._related_path("by_user"): {"patch", "put", "post", "delete"},
            self._related_path("operation"): {"patch", "put", "post", "delete"},
        }
        for _path, _methods in _methods_not_allowed.items():
            for _method in _methods:
                with self.subTest(path=_path, method=_method):
                    _client_method = getattr(self.client, _method)
                    _resp = _client_method(_path)
                    self.assertEqual(_resp.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestAddonOperationInvocationRelatedView(APITestCase):
    _EXPOSED_RELATIONS = (
        "thru_addon",
        "by_user",
    )

    @classmethod
    def setUpTestData(cls):
        cls._invocation = _factories.AddonOperationInvocationFactory()

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._invocation.by_user.user_uri)
        self.enterContext(self._mock_osf.mocking())

    def _related_path(self, related_field):
        return reverse(
            "addon-operation-invocations-related",
            kwargs={
                "pk": self._invocation.pk,
                "related_field": related_field,
            },
        )

    def test_get_related(self):
        for _relation_name in self._EXPOSED_RELATIONS:
            with self.subTest(relation=_relation_name):
                _resp = self.client.get(self._related_path(_relation_name))
                self.assertEqual(_resp.status_code, HTTPStatus.OK)
                _content = json.loads(_resp.rendered_content)
                _data = _content["data"]
                if isinstance(_data, list):
                    _expected_ids = {
                        str(_related.id)
                        for _related in getattr(self._invocation, _relation_name)
                    }
                    _actual_ids = {_related_datum["id"] for _related_datum in _data}
                else:
                    _expected_ids = {str(getattr(self._invocation, _relation_name).id)}
                    _actual_ids = {_data["id"]}
                self.assertEqual(_actual_ids, _expected_ids)
