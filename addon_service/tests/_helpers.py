import contextlib
from collections import defaultdict
from unittest.mock import patch

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from rest_framework import exceptions as drf_exceptions
from rest_framework.test import APIRequestFactory
from rest_framework_json_api.utils import get_resource_type_from_model


class MockOSF:
    _configured_caller_uri: str | None = None
    _permissions: dict[str, dict[str, str | bool]]

    def __init__(self, permissions=None):
        """A lightweight, configurable  mock of OSF for testing remote permissions.

        Accepts a mapping of arbitrary resource_uris to user permissiosn and `public` status
        {
            'osf.io/abcde': {'osf.io/bcdef': 'write', 'osf.io/cdefg': 'admin', 'public': True},
            'osf.io/zyxwv': {'osf.io/yxwvut': 'read', 'public': False}
        }
        Intercepts 'get' requests and uses the request url and this mapping to generate a minimal
        response required for testing GravyValet's behavior.

        Users of the mock can either explicitly tell the Mock which user to assume a call is from,
        or they can include a cookie with the 'user_uri' in their GET request, and MockOSF will honor
        that user
        """
        self._permissions = defaultdict(dict)
        if permissions:
            self._permissions.update(permissions)

    @contextlib.contextmanager
    def mocking(self):
        with patch(
            "app.authentication.make_auth_request",
            side_effect=self._mock_user_check,
        ), patch(
            "addon_service.common.permissions.authenticate_resource",
            side_effect=self._mock_resource_check,
        ):
            yield self

    def configure_assumed_caller(self, caller_uri):
        self._configured_caller_uri = caller_uri

    def configure_user_role(self, user_uri, resource_uri, role):
        self._permissions[resource_uri][user_uri] = role

    def configure_resource_visibility(self, resource_uri, *, public=True):
        self._permissions[resource_uri]["public"] = public

    def _get_assumed_caller(self, cookies=None):
        if self._configured_caller_uri:
            return self._configured_caller_uri
        if cookies is not None:
            return cookies.get(settings.USER_REFERENCE_COOKIE)
        return None

    def _get_user_permissions(self, user_uri, resource_uri):
        # Use of defaultdict means this will always have some value
        role = self._permissions[resource_uri].get(user_uri)
        if role == "read":
            return ["read"]
        if role == "write":
            return ["read", "write"]
        if role == "admin":
            return ["read", "write", "admin"]
        if self._permissions[resource_uri].get("public", False):
            return ["read"]
        return []

    def _mock_user_check(self, *args, **kwargs):
        caller_uri = self._get_assumed_caller(cookies=kwargs.get("cookies"))
        return {"data": {"links": {"iri": caller_uri}}}

    def _mock_resource_check(self, request, uri, required_permission, *args, **kwargs):
        caller = self._get_assumed_caller(cookies=request.COOKIES)
        permissions = self._get_user_permissions(user_uri=caller, resource_uri=uri)
        if required_permission.lower() not in permissions:
            raise drf_exceptions.PermissionDenied
        return uri  # mimicking behavior from the check being mocked


# TODO: use this more often in tests
def jsonapi_ref(obj) -> dict:
    """return a jsonapi resource reference (as json-serializable dict)"""
    return {
        "type": get_resource_type_from_model(obj.__class__),
        "id": obj.pk,
    }


def get_test_request(user=None, method="get", path="", cookies=None):
    _factory_method = getattr(APIRequestFactory(), method)
    _request = _factory_method(path)  # note that path is optional for view tests
    _request.session = SessionStore()  # Add cookies if provided
    if cookies:
        for name, value in cookies.items():
            _request.COOKIES[name] = value
    return _request
