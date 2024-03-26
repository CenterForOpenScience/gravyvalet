import aiohttp

from addon_service.common import aiohttp_requestor
from addon_service.models import ConfiguredStorageAddon
from addon_toolkit.storage import (
    StorageAddon,
    StorageConfig,
)


def get_storage_addon_instance(
    aiohttp_session: aiohttp.ClientSession,
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
        network=aiohttp_requestor.get_requestor(
            aiohttp_session,
            _external_storage_service.api_base_url,
        ),
    )
