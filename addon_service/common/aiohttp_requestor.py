from asgiref.sync import async_to_sync
import dataclasses
import contextlib
import typing
from http import (  # type: ignore
    HTTPMethod,
    HTTPStatus,
)
from urllib.parse import (
    urljoin,
    urlsplit,
)

import aiohttp

from addon_toolkit.http_requestor import (
    HttpRequestInfo,
    HttpRequestor,
    HttpResponseInfo,
)


@dataclasses.dataclass
class AiohttpRequestInfo(HttpRequestInfo):
    http_method: HTTPMethod
    uri_path: str
    query: dict | None = None
    headers: dict | None = None


@dataclasses.dataclass
class AiohttpResponseInfo(HttpResponseInfo):
    http_status: HTTPStatus
    headers: dict | None = None

    async def json_content(self) -> typing.Any:
        ...  # TODO


__SINGLETON_CLIENT_SESSION: aiohttp.ClientSession | None = None


def get_client_session() -> aiohttp.ClientSession:
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is None:
        __SINGLETON_CLIENT_SESSION = aiohttp.ClientSession(
            cookie_jar=aiohttp.DummyCookieJar(),  # ignore all cookies
        )
    return __SINGLETON_CLIENT_SESSION


def close_client_session() -> None:
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is not None:
        _blocking_close = async_to_sync(__SINGLETON_CLIENT_SESSION.close)
        _blocking_close()


class AiohttpRequestor(HttpRequestor):
    request_info_cls = AiohttpRequestInfo
    response_info_cls = AiohttpResponseInfo

    @contextlib.asynccontextmanager
    async def send_request(self, request_info: HttpRequestInfo) -> HttpResponseInfo:
        async with get_client_session().request(
            request_info.http_method,
            get_full_url(prefix_url, request_info.relative_url),
            # TODO: content
            # TODO: auth
        ) as _response:
            yield AiohttpResponseInfo(_response.status)


def get_full_url(prefix_url: str, relative_url: str) -> str:
    """resolve a url relative to a given prefix

    like urllib.parse.urljoin, but return value guaranteed to start with the given `prefix_url`
    """
    _split_relative = urlsplit(relative_url)
    if _split_relative.scheme or _split_relative.netloc:
        raise ValueError(
            f'relative url may not include scheme or host (got "{relative_url}")'
        )
    if _split_relative.path.startswith("/"):
        raise ValueError(
            f'relative url may not be an absolute path starting with "/" (got "{relative_url}")'
        )
    _full_url = urljoin(prefix_url, relative_url)
    if not _full_url.startswith(prefix_url):
        raise ValueError(
            f'relative url may not alter the base url (maybe with dot segments "/../"? got "{relative_url}")'
        )
    return _full_url
