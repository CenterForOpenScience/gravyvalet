from django.core.management.base import BaseCommand

from addon_service.tasks.key_rotation import schedule_encryption_rotation__celery


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        _task = schedule_encryption_rotation__celery.apply_async()
        self.stdout.write(self.style.SUCCESS(f"scheduled task {_task}"))
