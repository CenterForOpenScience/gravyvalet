from django.apps import AppConfig


class AddonServiceConfig(AppConfig):
    name = "addon_service"

    def ready(self):
        # need to import openapi extensions here for them to be registered
        import addon_service.common.openapi_extensions  # noqa: F401
