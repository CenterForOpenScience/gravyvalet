import asyncio
from itertools import chain
from typing import (
    Any,
    Awaitable,
    Coroutine,
)


async def join[
    T
](*awaitables: Awaitable[list[T]] | Coroutine[Any, Any, list[T]]) -> list[T]:
    return [*chain.from_iterable(await asyncio.gather(*awaitables))]


async def join_list[
    T
](awaitables: list[Awaitable[list[T]] | Coroutine[Any, Any, list[T]]]) -> list[T]:
    return await join(*awaitables)
