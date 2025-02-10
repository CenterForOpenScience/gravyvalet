import enum
import functools
import logging
import re
from http import HTTPStatus

from asgiref.sync import async_to_sync
from django import http as django_http
from django.conf import settings
from django.core.exceptions import PermissionDenied

from addon_service.common import hmac as hmac_utils
from addon_service.common.aiohttp_session import get_singleton_client_session
from addon_toolkit import AddonCapabilities


__all__ = (
    "OSFPermission",
    "get_osf_user_uri",
    "has_osf_permission_on_resource",
)

_logger = logging.getLogger(__name__)

_OSF_HMAC_USER_HEADER = "X-Requesting-User-URI"
_OSF_HMAC_RESOURCE_HEADER = "X-Requested-Resource-URI"
_OSF_HMAC_PERMISSIONS_HEADER = "X-Requested-Resource-Permissions"
_OSF_HMAC_PERMISSIONS_DELIMITER = ";"  # see https://github.com/CenterForOpenScience/osf.io/blob/00a17ecdb666c07245a520de3ccd0f743822573b/osf/external/gravy_valet/auth_helpers.py#L66


class OSFPermission(enum.StrEnum):
    """permission values used by the osf api"""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

    @staticmethod
    def for_capabilities(capabilities: AddonCapabilities) -> "OSFPermission":
        if AddonCapabilities.UPDATE in capabilities:
            return OSFPermission.WRITE
        if AddonCapabilities.ACCESS in capabilities:
            return OSFPermission.READ
        raise ValueError(capabilities)


@async_to_sync
async def get_osf_user_uri(request: django_http.HttpRequest) -> str | None:
    """get a uri identifying the user making this request"""
    try:
        uri = _get_hmac_verified_user_iri(request)
        request.session["user_reference_uri"] = uri
        return uri
    except hmac_utils.RejectedHmac as e:
        _logger.critical(f"rejected hmac signature!?\n\tpath:{request.path}")
        raise PermissionDenied(e)
    except hmac_utils.NotUsingHmac:
        pass  # the only acceptable hmac-related error is not using hmac at all
    # not hmac -- ask osf

    if uri := request.session.get("user_reference_uri"):
        return uri

    _auth_headers = _get_osf_auth_headers(request)
    if not _auth_headers:
        return None
    # we must handle the case when old, already created sessions must somehow set user_reference_uri
    # TODO: delete after all existing osf sessions have been revoked/expired
    _client = await get_singleton_client_session()
    async with _client.get(_osfapi_me_url(), headers=_auth_headers) as _response:
        if HTTPStatus(_response.status).is_client_error:
            return None
        _response_content = await _response.json()
        uri = _iri_from_osfapi_resource(_response_content["data"])
        request.session["user_reference_uri"] = uri


@async_to_sync
async def has_osf_permission_on_resource(
    request: django_http.HttpRequest,
    resource_uri: str,
    required_permission: OSFPermission,
) -> bool:
    """check for a permission on a resource via the osf api"""
    try:
        return _has_hmac_verified_osf_permission(
            request, resource_uri, required_permission
        )
    except hmac_utils.RejectedHmac:
        _logger.critical(
            f"rejected hmac signature!?\n\tpath:{request.path}\n\tresource:{resource_uri}"
        )
        return False
    except hmac_utils.NotUsingHmac:
        pass  # the only acceptable hmac-related error is not using hmac at all
    # not hmac -- ask osf
    _client = await get_singleton_client_session()
    async with _client.get(
        _osfapi_guid_url(resource_uri),
        params={
            "resolve": "f",  # do not redirect to the referent
            "embed": "referent",  # instead, include the referent in the response
            "fields[nodes]": "current_user_permissions",
        },
        headers=[
            *_get_osf_auth_headers(request),
            ("Accept", "application/vnd.api+json"),  # jsonapi
        ],
    ) as _response:
        if not HTTPStatus(_response.status).is_success:
            return False  # nonexistent osfid (TODO: consider raising error?)
        _response_content = await _response.json()
        _embedded_referent = _response_content["data"]["embeds"]["referent"]
        try:
            _referent_data = _embedded_referent["data"]
        except KeyError:  # no `data` for referent implies no permission
            return False
        # 'current_user_permissions' includes only explicitly assigned 'read' permission,
        # but here we wish to consider public resources READ-able by anyone
        if required_permission == OSFPermission.READ:
            return bool(_referent_data)
        return (
            required_permission
            in _referent_data["attributes"]["current_user_permissions"]
        )


###
# module-private helpers

_HeaderList = list[tuple[str, str]]


@functools.cache  # compute only once
def _osfid_regex() -> re.Pattern:
    # NOTE: does not guarantee a valid/extant osfid, only extracts the part
    # of the uri that _might_ be a valid/extant osfid (check with your osf)
    _prefixes = "|".join(
        re.escape(_allowed_prefix.rstrip("/"))
        for _allowed_prefix in settings.ALLOWED_RESOURCE_URI_PREFIXES
    )
    return re.compile(
        f"^(?:{_prefixes})"  # starts with an allowed prefix,
        r"/(?P<osfid>[^/]+)"  # has exactly one path segment,
        "/?$"  # and perhaps has a trailing slash at the end.
    )


def _extract_osfid(osf_resource_uri: str):
    _osfid_match = _osfid_regex().fullmatch(osf_resource_uri)
    if not _osfid_match:
        raise ValueError(
            "expected short osf uri from a known osf"
            f" (got '{osf_resource_uri}';"
            f" known osfs: {settings.ALLOWED_RESOURCE_URI_PREFIXES})"
        )
    return _osfid_match["osfid"]


def _osfapi_guid_url(osf_resource_uri: str):
    _osfid = _extract_osfid(osf_resource_uri)
    return f"{settings.OSF_API_BASE_URL}/v2/guids/{_osfid}/"


def _osfapi_me_url():
    return f"{settings.OSF_API_BASE_URL}/v2/users/me/"


def _get_osf_auth_headers(request: django_http.HttpRequest) -> _HeaderList:
    return [
        *_osf_cookie_auth_headers(request),
        *_osf_token_auth_headers(request),
    ]


def _osf_cookie_auth_headers(request: django_http.HttpRequest) -> _HeaderList:
    _osf_user_cookie = request.COOKIES.get(settings.USER_REFERENCE_COOKIE)
    return (
        [("Cookie", f"{settings.USER_REFERENCE_COOKIE}={_osf_user_cookie}")]
        if _osf_user_cookie
        else []
    )


def _osf_token_auth_headers(request: django_http.HttpRequest) -> _HeaderList:
    _auth_header = request.headers.get("Authorization")
    return (
        [("Authorization", _auth_header)]
        if _auth_header and _auth_header.startswith("Bearer ")
        else []
    )


def _iri_from_osfapi_resource(osfapi_resource: dict) -> str:
    # osf api object representation has an unambiguous identifier at `links.iri`
    return osfapi_resource["links"]["iri"]


def _get_hmac_verified_user_iri(request: django_http.HttpRequest) -> str | None:
    _signed_headers = hmac_utils.get_signed_headers(
        request,
        settings.OSF_HMAC_KEY,
        settings.OSF_HMAC_EXPIRATION_SECONDS,
    )
    return _signed_headers.get(_OSF_HMAC_USER_HEADER)


def _has_hmac_verified_osf_permission(
    request: django_http.HttpRequest,
    resource_uri: str,
    required_permission: OSFPermission,
) -> bool:
    _signed_headers = hmac_utils.get_signed_headers(
        request,
        settings.OSF_HMAC_KEY,
        settings.OSF_HMAC_EXPIRATION_SECONDS,
    )
    _resource_uri = _signed_headers.get(_OSF_HMAC_RESOURCE_HEADER)
    _permissions = _signed_headers.get(_OSF_HMAC_PERMISSIONS_HEADER)
    return bool(
        _resource_uri == resource_uri
        and _permissions
        and required_permission.value
        in _permissions.split(_OSF_HMAC_PERMISSIONS_DELIMITER)
    )
