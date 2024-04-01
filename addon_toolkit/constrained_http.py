import contextlib
import dataclasses
import typing
from collections.abc import (
    Iterable,
    Mapping,
)
from functools import partialmethod
from http import (
    HTTPMethod,
    HTTPStatus,
)
from urllib.parse import quote
from wsgiref.headers import Headers


KeyValuePairs = Iterable[tuple[str, str]] | Mapping[str, str]


class Multidict(Headers):
    """multidict with string keys and string values, for iri queries or request headers

    can initialize from an iterable of key-value pairs:
    >>> Multidict([('a', 'a1'), ('a', 'a2')]).as_query_string()
    'a=a1&a=a2'

    ...or from a mapping (with single values only):
    >>> Multidict({'a': 'aval', 'b': 'bval'}).as_query_string()
    'a=aval&b=bval'

    ...or empty:
    >>> Multidict().as_query_string()
    ''

    use `_.add(key, value)` to add an entry, allowing for multiple values per key
    >>> _m = Multidict([('a', 'two'), ('7', '🐙')])
    >>> _m.add('a', 'three')
    >>> _m.as_query_string()
    'a=two&7=%F0%9F%90%99&a=three'

    use set-item syntax (`_[key] = value`) to overwrite existing values
    >>> _m['a'] = 'five'
    >>> _m.as_query_string()
    '7=%F0%9F%90%99&a=five'

    inherits `wsgiref.headers.Headers`, a string multidict conveniently in the standard library
    https://docs.python.org/3/library/wsgiref.html#wsgiref.headers.Headers
    """

    def __init__(self, key_value_pairs: KeyValuePairs | None = None):
        # allow initializing with any iterable or mapping type (`Headers` expects `list`)
        match key_value_pairs:
            case None:
                _headerslist = []
            case list():  # already a list, is fine
                _headerslist = key_value_pairs
            case Mapping():
                _headerslist = list(key_value_pairs.items())
            case _:  # assume iterable
                _headerslist = list(key_value_pairs)
        super().__init__(_headerslist)

    def add(self, key: str, value: str, **mediatype_params):
        """add a key-value pair (allowing other values to exist)

        alias of `wsgiref.headers.Headers.add_header`
        """
        super().add_header(key, value, **mediatype_params)

    def as_headers(self) -> bytes:
        """format as http headers

        same as calling `bytes()` on a `wsgiref.headers.Headers` object -- see
        https://docs.python.org/3/library/wsgiref.html#wsgiref.headers.Headers
        """
        return super().__bytes__()

    def as_query_string(self) -> str:
        """format as query string, url-quoting parameter names and values"""
        return "&".join(
            "=".join((quote(_param_name), quote(_param_value)))
            for _param_name, _param_value in self.items()
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
    def http_status(self) -> HTTPStatus:
        ...

    @property
    def headers(self) -> Multidict:
        ...

    async def json_content(self) -> typing.Any:
        ...

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
    ) -> contextlib.AbstractAsyncContextManager[HttpResponseInfo]:
        ...


class HttpRequestor(typing.Protocol):
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
        http_method: HTTPMethod,
        uri_path: str,
        query: Multidict | KeyValuePairs | None = None,
        headers: Multidict | KeyValuePairs | None = None,
    ):
        _request_info = HttpRequestInfo(
            http_method=http_method,
            uri_path=uri_path,
            query=(query if isinstance(query, Multidict) else Multidict(query)),
            headers=(headers if isinstance(headers, Multidict) else Multidict(headers)),
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
