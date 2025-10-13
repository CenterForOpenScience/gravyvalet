from importlib import import_module

import itsdangerous
from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers


SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def ensure_str(value):
    if isinstance(value, bytes):
        return value.decode()
    return value


class UnsignCookieSessionMiddleware(SessionMiddleware):
    """
    Overrides the process_request hook of SessionMiddleware to retrieve the session key for finding/setting the
    correct session by unsigning/signing the cookie value using server secret.
    """

    def process_request(self, request):
        cookie = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            try:
                session_key = ensure_str(
                    itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET).unsign(cookie)
                )
            except itsdangerous.BadSignature:
                request.session = SessionStore
                return None
            request.session = SessionStore(session_key=session_key)
        else:
            request.session = SessionStore()

    def process_response(self, request, response):
        """
        If `request.session` was modified, or if the configuration is to save the session every time, save the changes
        and set a session cookie. This is port from `SessionMiddleware.process_response` with the following changes:
        1) Sign cookie value using server secret.
        2) Don't delete cookie.
        3) Don't set `Max-Age` or `Expires`
        """
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        if accessed:
            patch_vary_headers(response, ("Cookie",))

        # GV only accesses or modifies OSF cookie, but does not delete it. OSF handles the creation and deletion.
        if settings.SESSION_COOKIE_NAME in request.COOKIES and empty:
            return response

        if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
            if response.status_code < 500:
                try:
                    request.session.save()
                except UpdateError:
                    raise SessionInterrupted(
                        "The request's session was deleted before the request completed. "
                        "The user may have logged out in a concurrent request, for example."
                    )
                response.set_cookie(
                    settings.SESSION_COOKIE_NAME,
                    ensure_str(
                        itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET).sign(
                            request.session.session_key
                        )
                    ),
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    secure=settings.SESSION_COOKIE_SECURE,
                    httponly=settings.SESSION_COOKIE_HTTPONLY,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )

        return response
