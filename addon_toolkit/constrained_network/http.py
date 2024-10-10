import contextlib
import dataclasses
import typing
from functools import partialmethod
from http import (
    HTTPMethod,
    HTTPStatus,
)
from typing import Callable

from addon_toolkit.iri_utils import (
    KeyValuePairs,
    Multidict,
)


__all__ = (
    "HttpRequestInfo",
    "HttpResponseInfo",
    "HttpRequestor",
)


@dataclasses.dataclass
class HttpRequestInfo:
    http_method: HTTPMethod
    uri_path: str
    query: Multidict
    headers: Multidict
    json: dict
    # TODO: content (when needed)


class HttpResponseInfo(typing.Protocol):
    @property
    def http_status(self) -> HTTPStatus: ...

    @property
    def headers(self) -> Multidict: ...

    async def json_content(self) -> typing.Any: ...

    # TODO: streaming (when needed)


class _MethodRequestMethod(typing.Protocol):
    """structural type for the convenience methods HttpRequestor has per http method

    (name is joke: "method" has different but colliding meanings in http and python)
    """

    def __call__(
        self,
        uri_path: str,
        query: Multidict | KeyValuePairs | None = None,
        headers: Multidict | KeyValuePairs | None = None,
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]: ...


class HttpRequestor(typing.Protocol):
    """an abstract protocol for sending http requests (allowing different implementations)"""

    @property
    def response_info_cls(self) -> type[HttpResponseInfo]: ...

    def add_header_transformation_callback(
        self, callback: Callable[[dict], dict]
    ) -> None: ...

    # abstract method for subclasses
    def _do_send(
        self, request: HttpRequestInfo
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]: ...

    @contextlib.asynccontextmanager
    async def request(
        self,
        http_method: HTTPMethod,
        uri_path: str,
        query: Multidict | KeyValuePairs | None = None,
        headers: Multidict | KeyValuePairs | None = None,
        json: dict | None = None,
    ):
        _request_info = HttpRequestInfo(
            http_method=http_method,
            uri_path=uri_path,
            query=query,
            headers=(headers if isinstance(headers, Multidict) else Multidict(headers)),
            json=json,
        )
        async with self._do_send(_request_info) as _response:
            yield _response

    # TODO: streaming send/receive (only if/when needed)

    ###
    # convenience methods for http methods
    # (same call signature as self.request, minus `http_method`)

    OPTIONS: _MethodRequestMethod = partialmethod(request, HTTPMethod.OPTIONS)
    HEAD: _MethodRequestMethod = partialmethod(request, HTTPMethod.HEAD)
    GET: _MethodRequestMethod = partialmethod(request, HTTPMethod.GET)
    PATCH: _MethodRequestMethod = partialmethod(request, HTTPMethod.PATCH)
    POST: _MethodRequestMethod = partialmethod(request, HTTPMethod.POST)
    PUT: _MethodRequestMethod = partialmethod(request, HTTPMethod.PUT)
    DELETE: _MethodRequestMethod = partialmethod(request, HTTPMethod.DELETE)
