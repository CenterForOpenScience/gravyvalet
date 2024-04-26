from addon_service.common.aiohttp_session import get_singleton_client_session__blocking
from addon_service.common.network import GravyvaletHttpRequestor
from addon_service.models import ConfiguredStorageAddon
from addon_toolkit.storage import (
    StorageAddonProtocol,
    StorageConfig,
)


def get_storage_addon_instance(
    configured_storage_addon: ConfiguredStorageAddon,
) -> StorageAddonProtocol:
    _account = configured_storage_addon.base_account
    _external_storage_service = _account.external_storage_service
    _imp_cls = _external_storage_service.addon_imp.imp_cls
    return _imp_cls(
        config=StorageConfig(
            max_upload_mb=_external_storage_service.max_upload_mb,
        ),
        network=GravyvaletHttpRequestor(
            client_session=get_singleton_client_session__blocking(),
            prefix_url=_external_storage_service.api_base_url,
            account=_account,
        ),
    )
