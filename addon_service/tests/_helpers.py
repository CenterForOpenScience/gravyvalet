from functools import wraps
from unittest.mock import patch

import httpx
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.test import APIRequestFactory

from app import settings


def get_test_request(user=None, method="get", path="", cookies=None):
    _factory_method = getattr(APIRequestFactory(), method)
    _request = _factory_method(path)  # note that path is optional for view tests
    _request.session = SessionStore()  # Add cookies if provided
    if cookies:
        for name, value in cookies.items():
            _request.COOKIES[name] = value
    return _request


def with_mocked_httpx_get(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Use 'self' to access the current user, we need to have their
        # details to confirm auth test behavior
        current_user = getattr(self, "_user", None)

        with patch("httpx.Client") as MockClient:
            MockClient.return_value = MockHTTPXClient(current_user=current_user)
            return func(self, *args, **kwargs)

    return wrapper


def with_mocked_httpx_get_403(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Use 'self' to access the current user, we need to have their
        # details to confirm auth test behavior
        current_user = getattr(self, "_user", None)

        with patch("httpx.Client") as MockClient:
            MockClient.return_value = MockHTTPXClient403(current_user=current_user)
            return func(self, *args, **kwargs)

    return wrapper


class MockHTTPXClient:
    current_user = None
    expected_resource = None

    def __init__(self, *args, **kwargs):
        # Capture any arguments passed to the client
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get(self, url, *args, **kwargs):
        if url == settings.USER_REFERENCE_LOOKUP_URL:
            payload = {
                "data": {
                    "links": {"iri": self.kwargs["current_user"].user_uri},
                }
            }
            return httpx.Response(
                status_code=200,
                json=payload,
            )
        else:
            guid = url.rstrip("/").split("/")[-1]
            payload = {
                "data": {
                    "attributes": {
                        "current_user_permissions": ["read", "write", "admin"]
                    },
                    "links": {"iri": f"{settings.URI_ID}{guid}"},
                }
            }
            return httpx.Response(
                status_code=200,
                json=payload,
            )


class MockHTTPXClient403:
    def __init__(self, *args, **kwargs):
        # Capture any arguments passed to the client
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get(self, url, *args, **kwargs):
        return httpx.Response(
            status_code=403,
        )
