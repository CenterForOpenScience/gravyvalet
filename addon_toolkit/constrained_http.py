import contextlib
import dataclasses
import typing
from collections.abc import (
    Iterable,
    Mapping,
)
from functools import partialmethod
from http import (  # type: ignore
    HTTPMethod,
    HTTPStatus,
)
from urllib.parse import quote
from wsgiref.headers import Headers


KeyValuePairs = Iterable[tuple[str, str]] | Mapping[str, str]


class Multidict(Headers):
    """multidict of string keys and string values

    using `wsgiref.headers.Headers`, a string multidict conveniently in the standard library
    """

    def __init__(self, key_value_pairs: KeyValuePairs):
        # allow initializing with any iterable or mapping type, tho parent expects `list`
        match key_value_pairs:
            case list():  # already a list, is fine
                _headerslist = key_value_pairs
            case Mapping():
                _headerslist = list(key_value_pairs.items())
            case _:  # assume iterable
                _headerslist = list(key_value_pairs)
        super().__init__(_headerslist)


class HttpHeaders(Multidict):
    """multidict for http headers

    same as `wsgiref.headers.Headers` with a more friendly constructor
    """

    ...


class IriQuery(Multidict):
    """multidict for iri query parameters

    same as `wsgiref.headers.Headers` with a more friendly constructor
    and serialization to iri query string when passed to `str()`
    """

    def __str__(self):
        """format as query string, url-quoting parameter names and values"""
        return "&".join(
            "=".join((quote(_param_name), quote(_param_value)))
            for _param_name, _param_value in self.items()
        )


@dataclasses.dataclass  # this protocol is also a dataclass, to guarantee a constructor
class HttpRequestInfo(typing.Protocol):
    http_method: HTTPMethod
    uri_path: str
    query: IriQuery | None = None
    headers: HttpHeaders | None = None

    # TODO: content


class HttpResponseInfo(typing.Protocol):
    @property
    def http_status(self) -> HTTPStatus:
        ...

    @property
    def headers(self) -> HttpHeaders:
        ...

    async def json_content(self) -> typing.Any:
        ...


class _MethodRequestMethod(typing.Protocol):
    """structural type for the convenience methods HttpRequestor has per http method

    (name is joke: "method" has different but colliding meanings in http and python)
    """

    def __call__(
        self,
        uri_path: str,
        query: IriQuery | Iterable[tuple[str, str]] | Mapping[str, str],
        headers: HttpHeaders | Iterable[tuple[str, str]] | Mapping[str, str],
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]:
        ...


class HttpRequestor(typing.Protocol):
    @property
    def request_info_cls(self) -> type[HttpRequestInfo]:
        ...

    @property
    def response_info_cls(self) -> type[HttpResponseInfo]:
        ...

    # abstract method for subclasses
    def send(
        self,
        request: HttpRequestInfo,
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]:
        ...

    @contextlib.asynccontextmanager
    async def request(
        self,
        # same call signature as HttpRequestInfo constructor:
        http_method: HTTPMethod,
        uri_path: str,
        query: IriQuery | dict[str, str] | None = None,
        headers: HttpHeaders | dict[str, str] | None = None,
    ):
        _request_info = self.request_info_cls(
            http_method=http_method,
            uri_path=uri_path,
            query=(IriQuery(query.items()) if isinstance(query, dict) else query),
            headers=(
                HttpHeaders(headers.items()) if isinstance(headers, dict) else headers
            ),
        )
        async with self.send(_request_info) as _response:
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
