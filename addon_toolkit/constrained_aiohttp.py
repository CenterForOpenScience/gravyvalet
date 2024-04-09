import contextlib
import dataclasses
import logging
import typing
import weakref
from http import HTTPStatus
from urllib.parse import (
    urljoin,
    urlsplit,
)

import aiohttp  # type: ignore[import-not-found]

from addon_toolkit.constrained_http import (
    HttpRequestInfo,
    HttpRequestor,
    HttpResponseInfo,
    Multidict,
)


__all__ = ("AiohttpRequestor",)


_logger = logging.getLogger(__name__)


class _AiohttpResponseInfo(HttpResponseInfo):
    """an imp-friendly face for an aiohttp response (without exposing aiohttp to imps)"""

    def __init__(self, response: aiohttp.ClientResponse):
        _PrivateResponse(response).assign(self)

    @property
    def http_status(self) -> HTTPStatus:
        _response = _PrivateResponse.get(self).aiohttp_response
        return HTTPStatus(_response.status)

    @property
    def headers(self) -> Multidict:
        # TODO: allowed_headers config?
        _response = _PrivateResponse.get(self).aiohttp_response
        return Multidict(_response.headers.items())

    async def json_content(self) -> typing.Any:
        _response = _PrivateResponse.get(self).aiohttp_response
        return await _response.json()


class AiohttpRequestor(HttpRequestor):
    # abstract property from HttpRequestor:
    response_info_cls = _AiohttpResponseInfo

    def __init__(
        self,
        *,
        client_session: aiohttp.ClientSession,
        prefix_url: str,
        credentials: object,  # TODO: base credentials?
    ):
        _PrivateNetworkInfo(client_session, prefix_url, credentials).assign(self)

    # abstract method from HttpRequestor:
    @contextlib.asynccontextmanager
    async def send(self, request: HttpRequestInfo):
        _network = _PrivateNetworkInfo.get(self)
        _url = _network.get_full_url(request.uri_path)
        _logger.info(f"sending {request.http_method} to {_url}")
        async with _network.client_session.request(
            request.http_method,
            _url,
            headers=_network.get_headers(),
            # TODO: content
        ) as _response:
            yield _AiohttpResponseInfo(_response)


###
# for info or interfaces that should not be entangled with imps


class _PrivateInfo:
    """base class for conveniently assigning private info to an object

    >>> @dataclasses.dataclass
    >>> class _MyInfo(_PrivateInfo):
    ...     foo: str
    >>> _rando = object()
    >>> _MyInfo('woo').assign(_rando)
    >>> _MyInfo.get(_rando)
    _MyInfo(foo='woo')
    """

    __private_map: typing.ClassVar[weakref.WeakKeyDictionary]

    def __init_subclass__(cls):
        # each subclass gets its own private map -- this base class itself is unusable
        cls.__private_map = weakref.WeakKeyDictionary()

    @classmethod
    def get(cls, shared_obj: object):
        return cls.__private_map.get(shared_obj)

    def assign(self, shared_obj: object) -> None:
        self.__private_map[shared_obj] = self


@dataclasses.dataclass
class _PrivateResponse(_PrivateInfo):
    """ "private" info associated with an _AiohttpResponseInfo instance"""

    # avoid exposing aiohttp directly to imps
    aiohttp_response: aiohttp.ClientResponse


@dataclasses.dataclass
class _PrivateNetworkInfo(_PrivateInfo):
    """ "private" info associated with an AiohttpRequestor instance"""

    # avoid exposing aiohttp directly to imps
    client_session: aiohttp.ClientSession

    # keep network constraints away from imps
    prefix_url: str

    # protect credentials with utmost respect
    credentials: object  # TODO: base credentials dataclass? (or something)

    def get_headers(self) -> Multidict:
        # TODO: from self.credentials
        return Multidict({"Authorization": "Bearer --"})

    def get_full_url(self, relative_url: str) -> str:
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
        _full_url = urljoin(self.prefix_url, relative_url)
        if not _full_url.startswith(self.prefix_url):
            raise ValueError(
                f'relative url may not alter the base url (maybe with dot segments "/../"? got "{relative_url}")'
            )
        return _full_url
