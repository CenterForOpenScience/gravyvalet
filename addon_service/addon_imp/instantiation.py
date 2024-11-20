from __future__ import annotations

from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync

from addon_service.common.aiohttp_session import get_singleton_client_session
from addon_service.common.network import GravyvaletHttpRequestor
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import (
    CitationAddonImp,
    CitationConfig,
)
from addon_toolkit.interfaces.storage import (
    StorageAddonClientRequestorImp,
    StorageAddonHttpRequestorImp,
    StorageAddonImp,
    StorageConfig,
)


if TYPE_CHECKING:
    from addon_service.authorized_account.models import AuthorizedAccount
    from addon_service.models import (
        AuthorizedCitationAccount,
        AuthorizedStorageAccount,
    )


async def get_addon_instance(
    imp_cls: type[AddonImp],
    account: AuthorizedAccount,
    config: StorageConfig | CitationConfig,
) -> AddonImp:
    if issubclass(imp_cls, StorageAddonImp):
        return await get_storage_addon_instance(imp_cls, account, config)
    elif issubclass(imp_cls, CitationAddonImp):
        return await get_citation_addon_instance(imp_cls, account, config)
    raise ValueError(f"unknown addon type {imp_cls}")


get_addon_instance__blocking = async_to_sync(get_addon_instance)


async def get_storage_addon_instance(
    imp_cls: type[StorageAddonImp],
    account: AuthorizedStorageAccount,
    config: StorageConfig,
) -> StorageAddonImp:
    """create an instance of a `StorageAddonImp`

    (TODO: decide on a common constructor for all `AddonImp`s, remove this)
    """
    assert issubclass(imp_cls, StorageAddonImp)
    assert (
        imp_cls is not StorageAddonImp
    ), "Addons shouldn't directly extend StorageAddonImp"
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


async def get_citation_addon_instance(
    imp_cls: type[CitationAddonImp],
    account: AuthorizedCitationAccount,
    config: CitationConfig,
) -> CitationAddonImp:
    """create an instance of a `CitationAddonImp`"""

    assert issubclass(imp_cls, CitationAddonImp)
    return imp_cls(
        config=config,
        network=GravyvaletHttpRequestor(
            client_session=await get_singleton_client_session(),
            prefix_url=config.external_api_url,
            account=account,
        ),
    )
