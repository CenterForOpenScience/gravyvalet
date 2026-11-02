import importlib

from django.apps import AppConfig

from app.celery import app as celery_app


class AddonServiceConfig(AppConfig):
    name = "addon_service"

    def ready(self):
        from dj_control_room_base.models import BasePanelPlaceholder
        from django.contrib import admin

        # need to import openapi extensions here for them to be registered
        import addon_service.common.openapi_extensions  # noqa: F401

        # Workers import celery's `include` modules on startup; import them here too,
        # so this process registers the same tasks (e.g. for the dj-celery-panel overview)
        for module_name in celery_app.conf.include:
            importlib.import_module(module_name)

        # dj_control_room_base is installed only for dj_celery_panel's templates/static; hide its demo panel
        admin.site.unregister(BasePanelPlaceholder)
