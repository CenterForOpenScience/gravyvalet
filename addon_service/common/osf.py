import enum
import functools
import re
from http import HTTPStatus

from asgiref.sync import async_to_sync
from django import http as django_http
from django.conf import settings

from addon_service.common.aiohttp_session import get_singleton_client_session
from addon_toolkit import AddonCapabilities


__all__ = (
    "OSFPermission",
    "get_osf_user_uri",
    "has_osf_permission_on_resource",
)


class OSFPermission(enum.StrEnum):
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
    _auth_headers = _get_osf_auth_headers(request)
    if not _auth_headers:
        return None
    _client = await get_singleton_client_session()
    async with _client.get(_osfapi_me_url(), headers=_auth_headers) as _response:
        if HTTPStatus(_response.status).is_client_error:
            return None
        _response_content = await _response.json()
        return _iri_from_osfapi_resource(_response_content["data"])


@async_to_sync
async def has_osf_permission_on_resource(
    request: django_http.HttpRequest,
    resource_uri: str,
    required_permission: OSFPermission,
) -> bool:
    _client = await get_singleton_client_session()
    async with _client.get(
        _osfapi_guid_url(resource_uri),
        params={
            "resolve": "f",  # do not redirect to the referent
            "embed": "referent",  # instead, include the referent in the response
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
