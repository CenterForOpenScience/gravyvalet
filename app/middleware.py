from importlib import import_module

import itsdangerous
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware


SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def ensure_str(value):
    if isinstance(value, bytes):
        return value.decode()
    return value


class UnsignCookieSessionMiddleware(SessionMiddleware):
    """
    Overrides the process_request hook of SessionMiddleware
    to retrieve the session key for finding the correct session
    by unsigning the cookie value using server secret
    """

    def process_request(self, request):
        cookie = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            try:
                session_key = ensure_str(
                    itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET).unsign(cookie)
                )
            except itsdangerous.BadSignature:
                return None
            request.session = SessionStore(session_key=session_key)
        else:
            request.session = SessionStore()
