import base64
import hashlib
import hmac
import re
import urllib.parse
from datetime import (
    UTC,
    datetime,
)

from django.conf import settings


_AUTH_HEADER_REGEX = re.compile(
    r"^HMAC-SHA256 SignedHeaders=(?P<headers>[\w;-]*)&Signature=(?P<signature>[^\W_]*$)"
)


def _sign_message(message: str, hmac_key: str | None = None) -> str:
    key = hmac_key or settings.DEFAULT_HMAC_KEY
    encoded_message = base64.b64encode(message.encode())
    return hmac.new(
        key=key.encode(), digestmod=hashlib.sha256, msg=encoded_message
    ).hexdigest()


def _get_signed_components(
    request_url: str, request_method: str, body: str | bytes
) -> tuple[list[str], dict[str, str]]:
    parsed_url = urllib.parse.urlparse(request_url)
    if isinstance(body, str):
        body = body.encode()
    content_hash = hashlib.sha256(body).hexdigest() if body else None
    auth_timestamp = str(datetime.now(UTC))
    # Filter out query string and content_hash if none present
    signed_segments = [
        segment
        for segment in [
            request_method,
            parsed_url.path,
            parsed_url.query,
            auth_timestamp,
            content_hash,
        ]
        if segment
    ]
    signed_headers: dict[str, str] = {"X-Authorization-Timestamp": auth_timestamp}
    if content_hash:
        signed_headers["X-Content-SHA256"] = content_hash
    return signed_segments, signed_headers


def make_signed_headers(
    request_url: str,
    request_method: str,
    body: str | bytes = "",
    hmac_key: str | None = None,
) -> dict:
    signed_string_segments, signed_headers = _get_signed_components(
        request_url, request_method, body
    )
    signature = _sign_message(
        message="\n".join(signed_string_segments), hmac_key=hmac_key
    )

    signature_header_fields = ";".join(signed_headers.keys())
    auth_header_value = (
        f"HMAC-SHA256 SignedHeaders={signature_header_fields}&Signature={signature}"
    )
    return dict(
        **signed_headers,
        Authorization=auth_header_value,
    )


def _reconstruct_string_to_sign_from_request(request, signed_headers: list[str]) -> str:
    signed_segments = [request.method, request.path]
    query_string = request.META.get("QUERY_STRING")
    if query_string:
        signed_segments.append(query_string)
    signed_segments.extend(
        [str(request.headers[signed_header]) for signed_header in signed_headers]
    )
    return "\n".join([segment for segment in signed_segments if segment])


def validate_signed_headers(request, hmac_key=None):
    match = _AUTH_HEADER_REGEX.match(request.headers.get("Authorization", ""))
    if not match:
        raise ValueError(
            "Message was not authorized via valid HMAC-SHA256 signed headers"
        )
    expected_signature = match.group("signature")
    signed_headers = match.group("headers").split(";")

    computed_signature = _sign_message(
        message=_reconstruct_string_to_sign_from_request(
            request, signed_headers=signed_headers
        ),
        hmac_key=hmac_key,
    )
    if not hmac.compare_digest(computed_signature, expected_signature):
        raise ValueError("Could not verify HMAC signed request")

    content_hash = request.headers.get("X-Content-SHA256")
    if content_hash and not hmac.compare_digest(
        content_hash, hashlib.sha256(request.body).hexdigest()
    ):
        raise ValueError("Computed content hash did not match value from headers")
