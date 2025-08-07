from django.apps import AppConfig
from django.conf import settings


class AddonServiceConfig(AppConfig):
    name = "addon_service"

    def ready(self):
        # need to import openapi extensions here for them to be registered
        import addon_service.common.openapi_extensions  # noqa: F401
        from addon_service.common.known_imps import AddonRegistry

        AddonRegistry.register_addon_apps(settings.ADDON_APPS)
