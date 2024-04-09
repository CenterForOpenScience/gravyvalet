from asgiref.sync import async_to_sync

from addon_service.common.aiohttp_session import get_aiohttp_client_session
from addon_service.models import ConfiguredStorageAddon
from addon_toolkit.constrained_aiohttp import AiohttpRequestor
from addon_toolkit.storage import (
    StorageAddonProtocol,
    StorageConfig,
)


def get_storage_addon_instance(
    configured_storage_addon: ConfiguredStorageAddon,
) -> StorageAddonProtocol:
    _external_storage_service = (
        configured_storage_addon.base_account.external_storage_service
    )
    _imp_cls = _external_storage_service.addon_imp.imp_cls
    return _imp_cls(
        config=StorageConfig(
            max_upload_mb=_external_storage_service.max_upload_mb,
        ),
        network=AiohttpRequestor(
            client_session=async_to_sync(get_aiohttp_client_session)(),
            prefix_url=_external_storage_service.api_base_url,
            credentials=...,
        ),
    )
