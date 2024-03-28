import contextlib
import dataclasses
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

from addon_toolkit.constrained_http import (
    HttpHeaders,
    HttpRequestInfo,
    HttpRequestor,
    HttpResponseInfo,
    IriQuery,
)


@dataclasses.dataclass
class AiohttpRequestInfo(HttpRequestInfo):
    http_method: HTTPMethod
    uri_path: str
    query: IriQuery | None = None
    headers: HttpHeaders | None = None


@dataclasses.dataclass
class AiohttpResponseInfo(HttpResponseInfo):
    http_status: HTTPStatus
    headers: HttpHeaders

    @classmethod
    def from_aiohttp_response(cls, response: aiohttp.ClientResponse):
        return cls(
            HTTPStatus(response.status),
            HttpHeaders(list(response.headers.items())),
        )

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


async def close_client_session() -> None:
    # TODO: figure out if/where to call this (or decide it's unnecessary)
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is not None:
        await __SINGLETON_CLIENT_SESSION.close()


@dataclasses.dataclass(frozen=True)
class AiohttpRequestor(HttpRequestor):
    # dataclass fields:
    __prefix_url: str

    # abstract properties from HttpRequestor:
    request_info_cls = AiohttpRequestInfo
    response_info_cls = AiohttpResponseInfo

    @contextlib.asynccontextmanager
    async def send(self, request: HttpRequestInfo):
        # send request via singleton aiohttp client session
        async with get_client_session().request(
            request.http_method,
            get_full_url(self.__prefix_url, request.uri_path),
            # TODO: content
            # TODO: auth
        ) as _response:
            yield AiohttpResponseInfo.from_aiohttp_response(_response)


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
