from asgiref.sync import async_to_sync
from rest_framework_json_api import serializers

from addon_service.addon_imp.instantiation import get_addon_instance__blocking
from addon_service.configured_addon.models import ConfiguredAddon
from addon_toolkit import (
    credentials,
    json_arguments,
)


class WaterButlerConfigSerializer(serializers.Serializer):
    """Serialize ConfiguredStorageAddon information required by WaterButler.

    The returned data should share a shape with the existing `serialize_waterbutler_credentials`
    and `serialize_waterbutler_settings` functions used by the OSF-based Addons.

    NB: The Boa addon needs credentials from GV, and this seems like a good short-term
    place to hang it. Boa doesn't actually connect with WB, so this will probably be
    refactored in the future. But for now, any configured_storage_addon could actually
    be a configured_computed_addon.
    """

    class JSONAPIMeta:
        resource_name = "waterbutler-config"

    credentials = serializers.SerializerMethodField("_credentials_for_waterbutler")
    config = serializers.SerializerMethodField("_config_for_waterbutler")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wb_config = None

    def _credentials_for_waterbutler(self, configured_storage_addon):
        """NB: see class docstring about configured_storage_addon"""
        _creds_data = configured_storage_addon.credentials
        wb_config = self._config_for_waterbutler(configured_storage_addon)

        match type(_creds_data):
            case credentials.AccessTokenCredentials:
                creds = {"token": _creds_data.access_token}
                if "host" in wb_config:
                    creds["host"] = wb_config["host"]
                return creds
            case (
                credentials.AccessKeySecretKeyCredentials
                | credentials.UsernamePasswordCredentials
            ):
                # field names line up with waterbutler's expectations
                serialized_creds = json_arguments.json_for_dataclass(_creds_data)
                if "host" in wb_config:
                    serialized_creds["host"] = wb_config["host"]
                return serialized_creds
            case _:
                raise ValueError(f"unknown credentials type: {_creds_data}")

    def _config_for_waterbutler(self, configured_storage_addon: ConfiguredAddon):
        """NB: see class docstring about configured_storage_addon"""
        if not self._wb_config:
            self._wb_config = self._fetch_wb_config(configured_storage_addon)
        return self._wb_config

    @staticmethod
    def _fetch_wb_config(configured_storage_addon: ConfiguredAddon):
        """NB: see class docstring about configured_storage_addon"""
        imp = get_addon_instance__blocking(
            configured_storage_addon.imp_cls,
            configured_storage_addon.base_account,
            configured_storage_addon.config,
            require_network=False,
        )
        return async_to_sync(imp.build_wb_config)()
