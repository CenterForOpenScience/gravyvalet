from secrets import token_urlsafe
from urllib.parse import (
    urlencode,
    urlparse,
    urlunparse,
)


def build_auth_url(
    *, auth_uri, client_id, state_token, authorized_scopes, redirect_uri
):
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "state": state_token,
        "scope": authorized_scopes.join(",") if authorized_scopes else None,
        "redirect_uri": redirect_uri,
    }
    return urlunparse(urlparse(auth_uri)._replace(query=urlencode(query_params)))


def generate_state_token(token_length=16):
    return token_urlsafe(token_length)
