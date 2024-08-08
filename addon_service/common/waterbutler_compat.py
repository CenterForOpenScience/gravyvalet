from rest_framework_json_api import serializers

from addon_toolkit import (
    credentials,
    json_arguments,
)


class WaterButlerCredentialsSerializer(serializers.Serializer):
    """Serialize ConfiguredStorageAddon information required by WaterButler.

    The returned data should share a shape with the existing `serialize_waterbutler_credentials`
    and `serialize_waterbutler_settings` functions used by the OSF-based Addons.
    """

    class JSONAPIMeta:
        resource_name = "waterbutler-config"

    credentials = serializers.SerializerMethodField("_credentials_for_waterbutler")

    def _credentials_for_waterbutler(self, configured_storage_addon):
        _creds_data = configured_storage_addon.credentials
        match type(_creds_data):
            case credentials.AccessTokenCredentials:
                return {"token": _creds_data.access_token}
            case (
                credentials.AccessKeySecretKeyCredentials
                | credentials.UsernamePasswordCredentials
            ):
                # field names line up with waterbutler's expectations
                return json_arguments.json_for_dataclass(_creds_data)
            case _:
                raise ValueError(f"unknown credentials type: {_creds_data}")
