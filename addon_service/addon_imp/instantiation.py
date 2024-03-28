import aiohttp

from addon_service.common.aiohttp_requestor import AiohttpRequestor
from addon_service.models import ConfiguredStorageAddon
from addon_toolkit.storage import (
    StorageAddon,
    StorageConfig,
)


def get_storage_addon_instance(
    configured_storage_addon: ConfiguredStorageAddon,
) -> StorageAddon:
    _external_storage_service = (
        configured_storage_addon.base_account.external_storage_service
    )
    _imp_cls = _external_storage_service.addon_imp.imp_cls
    return _imp_cls(
        config=StorageConfig(
            max_upload_mb=_external_storage_service.max_upload_mb,
        ),
        network=AiohttpRequestor(
            _external_storage_service.api_base_url,
        ),
    )
