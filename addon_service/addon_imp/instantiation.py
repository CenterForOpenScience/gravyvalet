from __future__ import annotations

from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync

from addon_service.common.aiohttp_session import get_singleton_client_session
from addon_service.common.network import GravyvaletHttpRequestor
from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    CitationConfig,
)
from addon_toolkit.interfaces.storage import (
    StorageAddonImp,
    StorageConfig,
)


if TYPE_CHECKING:
    from addon_service.models import (
        AuthorizedCitationAccount,
        AuthorizedStorageAccount,
    )


async def get_storage_addon_instance(
    imp_cls: type[StorageAddonImp],
    account: AuthorizedStorageAccount,
    config: StorageConfig,
) -> StorageAddonImp:
    """create an instance of a `StorageAddonImp`

    (TODO: decide on a common constructor for all `AddonImp`s, remove this)
    """
    assert issubclass(imp_cls, StorageAddonImp)
    return imp_cls(
        config=config,
        network=GravyvaletHttpRequestor(
            client_session=await get_singleton_client_session(),
            prefix_url=config.external_api_url,
            account=account,
        ),
    )


get_storage_addon_instance__blocking = async_to_sync(get_storage_addon_instance)
"""create an instance of a `StorageAddonImp`

(same as `get_storage_addon_instance`, for use in synchronous context
"""


async def get_citation_addon_instance(
    imp_cls: type[CitationAddonImp],
    account: AuthorizedCitationAccount,
    config: CitationConfig,
) -> CitationAddonImp:
    """create an instance of a `CitationAddonImp`"""
