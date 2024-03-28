import dataclasses
import typing
from http import (  # type: ignore
    HTTPMethod,
    HTTPStatus,
)


@dataclasses.dataclass  # this protocol is also a dataclass, to guarantee a constructor
class HttpRequestInfo(typing.Protocol):
    http_method: HTTPMethod
    uri_path: str
    query: dict | None = None
    headers: dict | None = None
    # TODO: content


class HttpResponseInfo(typing.Protocol):
    @property
    def http_status(self) -> HTTPStatus:
        ...

    @property
    def headers(self) -> dict:
        ...

    async def json_content(self) -> typing.Any:
        ...


class HttpRequestor(typing.Protocol):
    @property
    def request_info_cls(self) -> type[HttpRequestInfo]:
        ...

    @property
    def response_info_cls(self) -> type[HttpResponseInfo]:
        ...

    async def send_request(self, request: HttpRequestInfo) -> HttpResponseInfo:
        ...

    # TODO: streaming send/receive (only if/when needed)

    ###
    # convenience methods for http methods
    # (same call signature as HttpRequestInfo constructor, minus `http_method`)

    async def GET(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.GET,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def HEAD(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.HEAD,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def POST(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.POST,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def PUT(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.PUT,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def PATCH(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.PATCH,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def DELETE(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.DELETE,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )

    async def OPTIONS(
        self,
        uri_path: str,
        query: dict | None = None,
        headers: dict | None = None,
    ) -> HttpResponseInfo:
        return await self.send_request(
            self.request_info_cls(
                HTTPMethod.OPTIONS,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )
