import aiohttp
from asgiref.sync import async_to_sync


__all__ = (
    "get_singleton_client_session",
    "get_singleton_client_session__blocking",
    "close_singleton_client_session",
    "close_singleton_client_session__blocking",
)


__SINGLETON_CLIENT_SESSION: aiohttp.ClientSession | None = None


async def get_singleton_client_session() -> aiohttp.ClientSession:
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is None:
        __SINGLETON_CLIENT_SESSION = aiohttp.ClientSession(
            cookie_jar=aiohttp.DummyCookieJar(),  # ignore all cookies
        )
    return __SINGLETON_CLIENT_SESSION


async def close_singleton_client_session() -> None:
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is not None:
        await __SINGLETON_CLIENT_SESSION.close()
        __SINGLETON_CLIENT_SESSION = None


get_singleton_client_session__blocking = async_to_sync(get_singleton_client_session)
close_singleton_client_session__blocking = async_to_sync(close_singleton_client_session)
