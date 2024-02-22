import base64
import binascii
from urllib.parse import (
    urlparse,
    urlunparse,
)

import httpx
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework import (
    authentication,
    exceptions,
)


TODO: Improve dockerization of OSF so that we don't need this
def handle_redirects(response):
    """Redirect fix for localhost during local development."""
    if settings.DEBUG and response.status_code in {301, 302, 303, 307, 308}:
        location = response.headers.get("Location")
        if location:
            parsed_location = urlparse(location)
            if parsed_location.hostname == "localhost":
                new_loc = parsed_location._replace(
                    netloc="192.168.168.167:8000", scheme="http"
                )
                response.headers["Location"] = urlunparse(new_loc)


class SkipAuthMethod(exceptions.APIException):
    """Exception for skipping an authentication method."""


def authenticate_resource(request, uri, required_permission):
    resource_url = settings.RESOURCE_REFERENCE_LOOKUP_URL.format(
        uri.replace(settings.URI_ID, "").rstrip("/")
    )
    for auth_method in [_try_cookie_auth, _try_basic_auth, _try_token_auth]:
        try:
            data = auth_method(request, resource_url)
            if data:
                iri = data["data"]["links"]["iri"]
                permissions = (
                    data.get("data", {})
                    .get("attributes", {})
                    .get("current_user_permissions", [])
                )

                if required_permission not in permissions:
                    raise exceptions.PermissionDenied(
                        "User lacks required permission for this resource."
                    )
                request.session["resource_reference_permissions"] = permissions
                return iri
        except SkipAuthMethod:
            continue
    return None


class GVCombinedAuthentication(authentication.BaseAuthentication):
    """Authentication supporting session, basic, and token methods."""

    def authenticate(self, request):
        for auth_method in [_try_cookie_auth, _try_basic_auth, _try_token_auth]:
            try:
                data = auth_method(request, settings.USER_REFERENCE_LOOKUP_URL)
                if data:
                    request.session["user_reference_uri"] = data["data"]["links"]["iri"]
                    return AnonymousUser(), None
            except SkipAuthMethod:
                continue

    def authenticate_header(self, request):
        """Specify the auth header in WWW-Authenticate."""
        return True


def make_auth_request(url, **kwargs):
    """Perform auth request and process response."""
    with httpx.Client(
        follow_redirects=True,
        cookies=kwargs.pop("cookies", None),
        auth=kwargs.pop("auth", None),
        event_hooks={"response": [handle_redirects]},
    ) as client:
        response = client.get(url, **kwargs)
        exceptions_map = {
            400: exceptions.ValidationError("Invalid request."),
            401: exceptions.AuthenticationFailed("Invalid credentials."),
            403: exceptions.PermissionDenied("Access denied."),
            404: exceptions.NotFound("Resource not found."),
            410: exceptions.APIException("Resource gone.", code=410),
        }
        if response.status_code in exceptions_map:
            raise exceptions_map[response.status_code]
        return response.json()


def _try_cookie_auth(request, url):
    cookie = request.COOKIES.get(settings.USER_REFERENCE_COOKIE)
    if not cookie:
        raise SkipAuthMethod("Missing cookie.")
    return make_auth_request(url, cookies={settings.USER_REFERENCE_COOKIE: cookie})


def _try_token_auth(request, url):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise SkipAuthMethod("Bearer token missing.")
    return make_auth_request(url, headers={"Authorization": auth_header})


def _try_basic_auth(request, url):
    auth_header = authentication.get_authorization_header(request).decode("utf-8")
    if not auth_header.startswith("Basic "):
        raise SkipAuthMethod("Basic auth missing.")

    try:
        auth_decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        userid, password = auth_decoded.split(":", 1)
    except (TypeError, ValueError, binascii.Error):
        raise exceptions.AuthenticationFailed("Invalid basic auth credentials.")

    return make_auth_request(url, auth=(userid, password))
