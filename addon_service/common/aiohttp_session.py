import threading
import weakref
from typing import MutableMapping

import aiohttp
from aiohttp import ClientSession
from asgiref.sync import async_to_sync


__all__ = (
    "get_singleton_client_session",
    "get_singleton_client_session__blocking",
    "close_singleton_client_session",
    "close_singleton_client_session__blocking",
)

# an identifying user-agent: some providers' CDNs (e.g. Mendeley, behind Cloudflare)
# challenge or block requests sent with aiohttp's default `Python/x.y aiohttp/z` user-agent
USER_AGENT = "GravyValet/1.0"

__SINGLETON_CLIENT_SESSION_STORE: MutableMapping[threading.Thread, ClientSession] = (
    weakref.WeakKeyDictionary()
)


async def has_current_session():
    thread_id = threading.current_thread()
    return __SINGLETON_CLIENT_SESSION_STORE.get(thread_id, False)


async def get_singleton_client_session() -> aiohttp.ClientSession:
    """return a reusable aiohttp client session (thread-local singleton)"""
    thread_id = threading.current_thread()
    if thread_id not in __SINGLETON_CLIENT_SESSION_STORE:
        __SINGLETON_CLIENT_SESSION_STORE[thread_id] = aiohttp.ClientSession(
            cookie_jar=aiohttp.DummyCookieJar(),  # ignore all cookies
            headers={"User-Agent": USER_AGENT},
        )
    return __SINGLETON_CLIENT_SESSION_STORE[thread_id]


async def close_singleton_client_session() -> None:
    """close the reusable aiohttp client session (thread-local singleton)"""
    if session := await has_current_session():
        await session.close()


get_singleton_client_session__blocking = async_to_sync(get_singleton_client_session)
"""return a reusable aiohttp client session (thread-local singleton)

(same as `get_singleton_client_session`, for use in non-async context)
"""

close_singleton_client_session__blocking = async_to_sync(close_singleton_client_session)
"""close the reusable aiohttp client session (thread-local singleton)

(same as `close_singleton_client_session`, for use in non-async context)
"""
