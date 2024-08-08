from __future__ import annotations

from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync

from addon_service.common.aiohttp_session import get_singleton_client_session
from addon_service.common.network import GravyvaletHttpRequestor
from addon_toolkit.interfaces.storage import (
    StorageAddonClientRequestorImp,
    StorageAddonHttpRequestorImp,
    StorageAddonImp,
    StorageConfig,
)


if TYPE_CHECKING:
    from addon_service.models import AuthorizedStorageAccount


async def get_storage_addon_instance(
    imp_cls: type[StorageAddonImp],
    account: AuthorizedStorageAccount,
    config: StorageConfig,
) -> StorageAddonImp:
    """create an instance of a `StorageAddonImp`

    (TODO: decide on a common constructor for all `AddonImp`s, remove this)
    """
    assert issubclass(imp_cls, StorageAddonImp)
    if issubclass(imp_cls, StorageAddonHttpRequestorImp):
        imp = imp_cls(
            config=config,
            network=GravyvaletHttpRequestor(
                client_session=await get_singleton_client_session(),
                prefix_url=config.external_api_url,
                account=account,
            ),
        )
    if issubclass(imp_cls, StorageAddonClientRequestorImp):
        imp = imp_cls(credentials=await account.get_credentials__async(), config=config)

    return imp


get_storage_addon_instance__blocking = async_to_sync(get_storage_addon_instance)
"""create an instance of a `StorageAddonImp`

(same as `get_storage_addon_instance`, for use in synchronous context
"""
