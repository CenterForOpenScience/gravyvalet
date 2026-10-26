import asyncio
import logging
from http import HTTPStatus

from asgiref.sync import sync_to_async
from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema

from addon_service.models import (
    OAuth2ClientConfig,
    OAuth2TokenMetadata,
)
from addon_service.oauth2.utils import get_initial_access_token


_logger = logging.getLogger(__name__)

# https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2.1
_KNOWN_ERROR_CODES = frozenset(
    (
        "invalid_request",
        "unauthorized_client",
        "access_denied",
        "unsupported_response_type",
        "invalid_scope",
        "server_error",
        "temporarily_unavailable",
    )
)


# Exclude oAuth views from openapi schema as they are from internal use only
@extend_schema(exclude=True)
@transaction.non_atomic_requests  # async views and ATOMIC_REQUESTS do not mix
async def oauth2_callback_view(request):
    """
    Handles oauth callbacks for the GV

    see https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2
    """

    if "error" in request.GET:
        # query params are attacker-controlled: never reflect them, and never as html
        _error = request.GET["error"]
        _logger.warning(
            "oauth2 callback error=%r error_description=%r",
            _error[:100],
            request.GET.get("error_description", "")[:200],
        )
        return HttpResponse(
            "oauth2 authorization failed"
            + (f": {_error}" if _error in _KNOWN_ERROR_CODES else ""),
            status=HTTPStatus.BAD_REQUEST,
            content_type="text/plain; charset=utf-8",
        )
    _state_token = request.GET["state"]
    _authorization_code = request.GET["code"]
    _token_metadata, _oauth_client_config = await _resolve_state_token(_state_token)
    _fresh_token_result = await get_initial_access_token(
        token_endpoint_url=_oauth_client_config.token_endpoint_url,
        authorization_code=_authorization_code,
        auth_callback_url=_oauth_client_config.auth_callback_url,
        client_id=_oauth_client_config.client_id,
        client_secret=_oauth_client_config.client_secret,
    )
    _accounts = await _token_metadata.update_with_fresh_token(_fresh_token_result)
    await asyncio.gather(*[_account.execute_post_auth_hook() for _account in _accounts])
    return HttpResponse(status=HTTPStatus.OK)  # TODO: redirect


###
# module-private helpers


@sync_to_async
def _resolve_state_token(
    state_token: str,
) -> tuple[OAuth2TokenMetadata, OAuth2ClientConfig]:
    _token_metadata = OAuth2TokenMetadata.objects.get_by_state_token(state_token)
    return (_token_metadata, _token_metadata.client_details)
