import dataclasses

from rest_framework_json_api import serializers

from addon_service import models as db
from addon_toolkit import (
    credentials,
    json_arguments,
)


class WaterButlerConfigurationSerializer(serializers.Serializer):
    """Serialize ConfiguredStorageAddon information required by WaterButler.

    The returned data should share a shape with the existing `serialize_waterbutler_credentials`
    and `serialize_waterbutler_settings` functions used by the OSF-based Addons.
    """

    credentials = serializers.JSONField()
    settings = serializers.JSONField()

    def __init__(self, configured_storage_addon: db.ConfiguredStorageAddon):
        data = {
            "credentials": _format_credentials_for_waterbutler(
                configured_storage_addon.credentials
            ),
            "settings": _serialize_waterbutler_settings(configured_storage_addon),
        }
        super().__init__(data=data)
        self.is_valid()


def _format_credentials_for_waterbutler(creds_data):
    match type(creds_data):
        case credentials.AccessTokenCredentials:
            return {"token": creds_data.access_token}
        case (
            credentials.AccessKeySecretKeyCredentials
            | credentials.UsernamePasswordCredentials
        ):
            # field names line up with waterbutler's expectations
            return dataclasses.asdict(creds_data)
        case _:
            raise ValueError(f"unknown credentials type: {creds_data}")


def _serialize_waterbutler_settings(
    configured_storage_addon: db.ConfiguredStorageAddon,
):
    """An ugly compatibility layer between GravyValet and WaterButler."""
    _wb_addon_settings = WaterbutlerAddonSettings(
        external_api_url=configured_storage_addon.authorized_storage_account.api_base_url,
        connected_root=configured_storage_addon.root_folder,
        provider_key=configured_storage_addon.external_service.waterbutler_provider_key,
        external_account_id="...",  # TODO
    )
    return json_arguments.json_for_dataclass(_wb_addon_settings)


@dataclasses.dataclass
class WaterbutlerAddonSettings:
    external_api_url: str
    connected_root: str  # may be path or id
    provider_key: (
        str  # required for WB to support multiple connected addons for the same service
    )
    external_account_id: str | None = None
