import contextlib
import dataclasses
import typing
from functools import partialmethod
from http import (
    HTTPMethod,
    HTTPStatus,
)

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
    @property
    def response_info_cls(self) -> type[HttpResponseInfo]: ...

    # abstract method for subclasses
    def send_request(
        self, request: HttpRequestInfo
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]: ...

    @contextlib.asynccontextmanager
    async def _request(
        self,
        http_method: HTTPMethod,
        uri_path: str,
        query: Multidict | KeyValuePairs | None = None,
        headers: Multidict | KeyValuePairs | None = None,
    ) -> typing.Any:  # loose type; method-specific methods below are more accurate
        _request_info = HttpRequestInfo(
            http_method=http_method,
            uri_path=uri_path,
            query=(query if isinstance(query, Multidict) else Multidict(query)),
            headers=(headers if isinstance(headers, Multidict) else Multidict(headers)),
        )
        async with self.send_request(_request_info) as _response:
            yield _response

    # TODO: streaming send/receive (only if/when needed)

    ###
    # convenience methods for http methods
    # (same call signature as self.request, minus `http_method`)

    OPTIONS: _MethodRequestMethod = partialmethod(_request, HTTPMethod.OPTIONS)
    HEAD: _MethodRequestMethod = partialmethod(_request, HTTPMethod.HEAD)
    GET: _MethodRequestMethod = partialmethod(_request, HTTPMethod.GET)
    PATCH: _MethodRequestMethod = partialmethod(_request, HTTPMethod.PATCH)
    POST: _MethodRequestMethod = partialmethod(_request, HTTPMethod.POST)
    PUT: _MethodRequestMethod = partialmethod(_request, HTTPMethod.PUT)
    DELETE: _MethodRequestMethod = partialmethod(_request, HTTPMethod.DELETE)
