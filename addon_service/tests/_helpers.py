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


def with_mocked_httpx_get(response_status=200):
    """Decorator to mock httpx.Client get requests with a customizable response status."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            with patch("httpx.Client.get", new=lambda *args, **kwargs: mock_httpx_response(*args, response_status=response_status)):
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


def mock_httpx_response(url, current_user, response_status, *args, **kwargs):
    """Generates mock httpx.Response based on the requested URL and response status."""
    if response_status == 200:
        if url == settings.USER_REFERENCE_LOOKUP_URL:
            payload = {"data": {"links": {"iri": current_user.user_uri}}}
        else:
            guid = url.rstrip("/").split("/")[-1]
            payload = {
                "data": {
                    "attributes": {"current_user_permissions": ["read", "write", "admin"]},
                    "links": {"iri": f"{settings.URI_ID}{guid}"}
                }
            }
        return httpx.Response(status_code=200, json=payload)
    else:  # Handles 403 and other statuses explicitly
        return httpx.Response(status_code=response_status)