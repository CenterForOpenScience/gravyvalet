from __future__ import annotations

import contextlib
import dataclasses
import secrets
from collections import defaultdict
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
)
from unittest.mock import (
    AsyncMock,
    patch,
)
from urllib.parse import (
    parse_qs,
    urlparse,
)

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common.aiohttp_session import get_singleton_client_session


if TYPE_CHECKING:
    from addon_service.external_service.storage import ExternalStorageService


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
        with (
            patch(
                "addon_service.authentication.GVCombinedAuthentication.authenticate",
                side_effect=self._mock_user_check,
            ),
            patch(
                "addon_service.common.osf.has_osf_permission_on_resource",
                side_effect=self._mock_resource_check,
            ),
            patch_encryption_key_derivation(),
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

    def _mock_user_check(self, request) -> tuple[Any, Any] | None:
        # replaces `authenticate` on a custom rest_framework authenticator:
        # https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication
        caller_uri = self._get_assumed_caller(cookies=request.COOKIES)
        request.session["user_reference_uri"] = caller_uri
        return (
            (None, None)  # success! return a tuple (values here yet unused)
            if caller_uri
            else None  # failure! return None
        )

    def _mock_resource_check(self, request, uri, required_permission, *args, **kwargs):
        caller = self._get_assumed_caller(cookies=request.COOKIES)
        permissions = self._get_user_permissions(user_uri=caller, resource_uri=uri)
        return bool(required_permission.lower() in permissions)


class MockOAuth2ExternalService:
    def __init__(self, external_service):
        self._static_access_token = None
        self._static_refresh_token = None
        if external_service.oauth2_client_config is not None:
            self._auth_url = external_service.auth_uri
            self._token_endpoint_url = (
                external_service.oauth2_client_config.token_endpoint_url
            )
        self._local_routes = {
            external_service.oauth2_client_config.token_endpoint_url: "token_endpoint"
        }

    def set_internal_client(self, client):
        """Attach a DRF APIClient for making requests internally"""
        self._internal_client = client

    def configure_static_tokens(self, access=None, refresh=None):
        self._static_access_token = access
        self._static_refresh_token = refresh

    @contextlib.asynccontextmanager
    async def mocking(self):
        client_session = await get_singleton_client_session()
        with (
            patch.object(client_session, "get", new=self._route_get),
            patch.object(client_session, "post", new=self._route_post),
        ):
            yield self

    async def _route_get(self, url, *args, **kwargs):
        if url.startswith(self._auth_url):
            state_token = parse_qs(urlparse(url).query)["state"]
            await self._initiate_oauth_exchange(state_token=state_token)
        else:
            raise RuntimeError(f"Received unrecognized endpoint {url}")

    async def _initiate_oauth_exchange(self, state_token):
        await sync_to_async(self._internal_client.get)(
            reverse("oauth2-callback"), {"state": state_token, "code": "authgrant"}
        )
        return _FakeAiohttpResponse()

    @contextlib.asynccontextmanager
    async def _route_post(self, url, *args, **kwargs):
        if url.startswith(self._token_endpoint_url):
            yield _FakeAiohttpResponse(
                status=HTTPStatus.CREATED,
                data={
                    "access_token": self._static_access_token or secrets.token_hex(12),
                    "refresh_token": self._static_refresh_token
                    or secrets.token_hex(12),
                    "expires_in": 3600,
                },
            )
        else:
            raise RuntimeError(f"Received unrecognized endpoint {url}")


@dataclasses.dataclass
class MockOAuth1ServiceProvider:
    _external_service: ExternalStorageService
    _static_request_token: str
    _static_request_secret: str
    _static_verifier: str
    _static_oauth_token: str
    _static_oauth_secret: str

    def __post_init__(self):
        if self._external_service.oauth1_client_config is not None:
            self._access_token_url = (
                self._external_service.oauth1_client_config.access_token_url
            )
            self._request_token_url = (
                self._external_service.oauth1_client_config.request_token_url
            )

    @property
    def auth_url(self):
        return self._external_service.auth_url

    def set_internal_client(self, client):
        """Attach a DRF APIClient for making requests internally"""
        self._internal_client = client

    @contextlib.contextmanager
    def mocking(self):
        with patch(
            "addon_service.oauth1.utils.get_singleton_client_session",
            AsyncMock(return_value=AsyncMock(post=self._route_post)),
        ):
            yield self

    def initiate_oauth_exchange(self):
        self._internal_client.get(
            reverse("oauth1-callback"),
            {"oauth_token": "oauth_token", "oauth_verifier": "oauth_verifier"},
        )
        return _FakeAiohttpResponse()

    @contextlib.asynccontextmanager
    async def _route_post(self, url, *args, **kwargs):
        if url.startswith(self._access_token_url):
            yield _FakeAiohttpResponse(
                status=HTTPStatus.CREATED,
                data={
                    "oauth_token": self._static_oauth_token,
                    "oauth_token_secret": self._static_oauth_secret,
                },
            )
        elif url.startswith(self._request_token_url):
            yield _FakeAiohttpResponse(
                status=HTTPStatus.CREATED,
                data={
                    "oauth_token": self._static_request_token,
                    "oauth_token_secret": self._static_request_secret,
                    "oauth_verifier": self._static_verifier,
                },
            )
        else:
            raise RuntimeError(f"Received unrecognized endpoint {url}")


@dataclasses.dataclass
class _FakeAiohttpResponse:
    status: HTTPStatus = HTTPStatus.OK
    data: dict | None = None

    async def json(self):
        return self.data


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


@contextlib.contextmanager
def patch_encryption_key_derivation():
    _fake_secret = b"this is fine"
    _some_random_key = b"\xdd\xd1\xdfN9\n\xbb\xa5\x9a|\xc6\x1f\xd6b\xf2\xfc>\x1e\xfe\xfd\x14\xc6n\xd7\x18\xbf'\x04qk\x8c\xfb"

    with patch(
        "addon_service.credentials.encryption.settings.GRAVYVALET_ENCRYPT_SECRET",
        _fake_secret,
    ), patch(
        "addon_service.credentials.encryption.hashlib.scrypt",
        return_value=_some_random_key,
    ):
        yield
