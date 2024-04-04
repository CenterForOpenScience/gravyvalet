import threading

from django.apps import AppConfig

from app.celery import account_status_change_queue


class AddonServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addon_service"

    def ready(self):
        """
        This method is called as soon as the Django app is ready.
        It starts background threads to listen to specific queues for processing user-related signals.
        """
        super().ready()
        from addon_service.listeners import listen_to_queue_route

        threading.Thread(
            target=listen_to_queue_route,
            args=(account_status_change_queue,),
            daemon=True,
        ).start()
