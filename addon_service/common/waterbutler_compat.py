from rest_framework_json_api import serializers

from addon_toolkit import credentials


class WaterButlerConfigurationSerializer(serializers.Serializer):
    """Serialize ConfiguredStorageAccount information required by WaterButler.

    The returned data should share a shape with the existing `serialize_waterbutler_credentials`
    and `serialize_waterbutler_settings` functions used by the OSF-based Addons.
    """

    credentials = serializers.JSONField()
    settings = serializers.JSONField()

    def __init__(self, configured_storage_addon):
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
        case _:
            return creds_data.asdict()


def _serialize_waterbutler_settings(configured_storage_addon):
    """An ugly compatibility layer between GravyValet and WaterButler."""
    return {
        "folder": configured_storage_addon.root_folder,
        # This is required for WB to support multiple connected addons for the same service
        "service": _get_wb_provider_name_from_service_name(
            configured_storage_addon.external_service
        ),
    }


def _get_wb_provider_name_from_service_name(external_storage_service):
    match external_storage_service.name:
        case "boxdotcom":
            return "box"
        case _:
            return external_storage_service.name
