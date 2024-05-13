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

import aiohttp
from asgiref.sync import sync_to_async

from addon_service import models as db
from addon_service.common import exceptions
from addon_service.oauth import utils as oauth_utils
from addon_toolkit.constrained_network import (
    HttpRequestInfo,
    HttpRequestor,
    HttpResponseInfo,
)
from addon_toolkit.iri_utils import Multidict


__all__ = ("GravyvaletHttpRequestor",)


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


class GravyvaletHttpRequestor(HttpRequestor):
    # abstract property from HttpRequestor:
    response_info_cls = _AiohttpResponseInfo

    def __init__(
        self,
        *,
        client_session: aiohttp.ClientSession,
        prefix_url: str,
        account: db.AuthorizedStorageAccount,
    ):
        _PrivateNetworkInfo(client_session, prefix_url, account).assign(self)

    # abstract method from HttpRequestor:
    @contextlib.asynccontextmanager
    async def send_request(self, request: HttpRequestInfo):
        try:
            async with self._try_send(request) as _response:
                yield _response
        except exceptions.ExpiredAccessToken:
            await _PrivateNetworkInfo.get(self).refresh_oauth_access_token()
            # if this one fails, don't try refreshing again
            async with self._try_send(request) as _response:
                yield _response

    @contextlib.asynccontextmanager
    async def _try_send(self, request: HttpRequestInfo):
        _private = _PrivateNetworkInfo.get(self)
        _url = _private.get_full_url(request.uri_path)
        _logger.info(f"sending {request.http_method} to {_url}")
        async with _private.client_session.request(
            request.http_method,
            _url,
            headers=await _private.get_headers(),
            # TODO: content
        ) as _response:
            if _response.status == HTTPStatus.UNAUTHORIZED:
                # assume unauthorized because of token expiration.
                # if not, will fail again after refresh (which is fine)
                raise exceptions.ExpiredAccessToken
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
    """ "private" info associated with a GravyvaletHttpRequestor instance"""

    # avoid exposing aiohttp directly to imps
    client_session: aiohttp.ClientSession

    # keep network constraints away from imps
    prefix_url: str
    account: db.AuthorizedStorageAccount

    @sync_to_async
    def get_headers(self) -> Multidict:
        _headers = Multidict()
        _credentials = self.account.credentials
        if _credentials:
            _headers.add_many(self.account.credentials.iter_headers())
        return _headers

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

    @sync_to_async
    def _get_oauth_models(self) -> tuple[db.OAuth2ClientConfig, db.OAuth2TokenMetadata]:
        # wrap db access in `sync_to_async`
        return (
            self.account.external_service.oauth2_client_config,
            self.account.oauth2_token_metadata,
        )

    async def refresh_oauth_access_token(self) -> None:
        _oauth_client_config, _oauth_token_metadata = await self._get_oauth_models()
        _fresh_token_result = await oauth_utils.get_refreshed_access_token(
            token_endpoint_url=_oauth_client_config.token_endpoint_url,
            refresh_token=_oauth_token_metadata.refresh_token,
            auth_callback_url=_oauth_client_config.auth_callback_url,
            client_id=_oauth_client_config.client_id,
            client_secret=_oauth_client_config.client_secret,
        )
        await _oauth_token_metadata.update_with_fresh_token(_fresh_token_result)
