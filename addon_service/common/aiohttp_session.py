import threading
from threading import local

import aiohttp
from asgiref.sync import async_to_sync


__all__ = (
    "get_singleton_client_session",
    "get_singleton_client_session__blocking",
    "close_singleton_client_session",
    "close_singleton_client_session__blocking",
)

__SINGLETON_CLIENT_SESSION_STORE: threading.local = local()


async def get_singleton_client_session() -> aiohttp.ClientSession:
    """return a reusable aiohttp client session (thread-local singleton)"""
    if not _is_session_valid():
        __SINGLETON_CLIENT_SESSION_STORE.session = aiohttp.ClientSession(
            cookie_jar=aiohttp.DummyCookieJar(),  # ignore all cookies
        )
    return __SINGLETON_CLIENT_SESSION_STORE.session


def _is_session_valid() -> bool:
    return (
        hasattr(__SINGLETON_CLIENT_SESSION_STORE, "session")
        and isinstance(__SINGLETON_CLIENT_SESSION_STORE.session, aiohttp.ClientSession)
        and not __SINGLETON_CLIENT_SESSION_STORE.session.closed
    )


async def close_singleton_client_session() -> None:
    """close the reusable aiohttp client session (thread-local singleton)"""
    if _is_session_valid():
        await __SINGLETON_CLIENT_SESSION_STORE.close()
        __SINGLETON_CLIENT_SESSION_STORE.session = None


get_singleton_client_session__blocking = async_to_sync(get_singleton_client_session)
"""return a reusable aiohttp client session (thread-local singleton)

(same as `get_singleton_client_session`, for use in non-async context)
"""

close_singleton_client_session__blocking = async_to_sync(close_singleton_client_session)
"""close the reusable aiohttp client session (thread-local singleton)

(same as `close_singleton_client_session`, for use in non-async context)
"""
