import aiohttp
from asgiref.sync import async_to_sync


__all__ = (
    "get_aiohttp_client_session",
    "close_aiohttp_client_session",
    "close_aiohttp_client_session_sync",
)


__SINGLETON_CLIENT_SESSION: aiohttp.ClientSession | None = None


def get_aiohttp_client_session() -> aiohttp.ClientSession:
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is None:
        __SINGLETON_CLIENT_SESSION = async_to_sync(_start_aiohttp_client_session)()
    return __SINGLETON_CLIENT_SESSION


async def close_aiohttp_client_session() -> None:
    # TODO: figure out if/where to call this (or decide it's unnecessary)
    global __SINGLETON_CLIENT_SESSION
    if __SINGLETON_CLIENT_SESSION is not None:
        await __SINGLETON_CLIENT_SESSION.close()
        __SINGLETON_CLIENT_SESSION = None


close_aiohttp_client_session_sync = async_to_sync(close_aiohttp_client_session)


async def _start_aiohttp_client_session() -> aiohttp.ClientSession:
    # start session in a coroutine to guarantee some event loop
    return aiohttp.ClientSession(
        cookie_jar=aiohttp.DummyCookieJar(),  # ignore all cookies
    )
