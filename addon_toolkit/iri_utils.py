from collections.abc import (
    Iterable,
    Mapping,
)
from urllib.parse import (
    urlencode,
    urlsplit,
    urlunsplit,
)
from wsgiref.headers import Headers


__all__ = (
    "KeyValuePairs",
    "Multidict",
    "iri_with_query",
)


KeyValuePairs = Iterable[tuple[str, str]] | Mapping[str, str]
"""a type alias allowing multiple ways to convey key-value pairs"""


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

    def add_many(self, pairs: Iterable[tuple[str, str]]):
        for _key, _value in pairs:
            self.add(_key, _value)

    def as_headers(self) -> bytes:
        """format as http headers

        same as calling `bytes()` on a `wsgiref.headers.Headers` object -- see
        https://docs.python.org/3/library/wsgiref.html#wsgiref.headers.Headers
        """
        return super().__bytes__()

    def as_query_string(self) -> str:
        """format as query string, url-quoting parameter names and values"""
        return urlencode(self.items())


def iri_with_query(iri: str, query_params: KeyValuePairs | Multidict) -> str:
    """build a new iri with the given query params (replacing the iri's query string)

    `query_params` may be a dictionary (with string keys and values):
    >>> iri_with_query('http://foo.example/hello?q=p', {'a': 'z'})
    'http://foo.example/hello?a=z'

    ...or an iterable of key-value pairs:
    >>> iri_with_query('http://foo.example/hello?q=p', [('a', 'z')])
    'http://foo.example/hello?a=z'

    ...or a Multidict instance:
    >>> _qp = Multidict()
    >>> _qp.add('a', 'z')
    >>> iri_with_query('http://foo.example/hello?q=p', _qp)
    'http://foo.example/hello?a=z'
    """
    _qp_multidict = (
        query_params if isinstance(query_params, Multidict) else Multidict(query_params)
    )
    return urlunsplit(urlsplit(iri)._replace(query=_qp_multidict.as_query_string()))
