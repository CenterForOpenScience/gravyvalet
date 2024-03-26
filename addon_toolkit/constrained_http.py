import dataclasses
import typing
from http import (  # type: ignore
    HTTPMethod,
    HTTPStatus,
)


@dataclasses.dataclass
class HttpRequestInfo:
    http_method: HTTPMethod
    uri_path: str
    query: dict | None = None
    headers: dict | None = None
    # TODO: content


@dataclasses.dataclass
class HttpResponseInfo:
    for_request: HttpRequestInfo
    http_status: HTTPStatus
    headers: dict | None = None
    # TODO: content


class HttpRequestor(typing.Protocol):
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
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
    ):
        return await self.send_request(
            HttpRequestInfo(
                HTTPMethod.OPTIONS,
                uri_path=uri_path,
                query=query,
                headers=headers,
            )
        )
