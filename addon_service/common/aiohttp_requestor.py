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


def get_requestor(
    aiohttp_session: aiohttp.ClientSession,
    prefix_url: str,
) -> HttpRequestor:
    # defining this class inside a function to include the ClientSession via closure
    # (avoid offering imps internals like aiohttp, prefer constrained HttpRequestor)
    class _AiohttpRequestor(HttpRequestor):
        async def send_request(self, request_info: HttpRequestInfo) -> HttpResponseInfo:
            async with aiohttp_session.request(
                request_info.http_method,
                get_full_url(prefix_url, request_info.relative_url),
                # TODO: content
                # TODO: auth
            ) as _response:
                return HttpResponseInfo(_response.status)

    return _AiohttpRequestor()


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
