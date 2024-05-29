from celery import Celery
from kombu import (
    Exchange,
    Queue,
)

from app import settings


account_status_change_queue = Queue(
    settings.EXCHANGE_NAME,
    Exchange(settings.EXCHANGE_NAME),
)

# Assuming 'app' is your Celery app instance
app = Celery()
app.conf.update(
    broker_url=settings.OSF_BROKER_URL,
    task_default_exchange=settings.EXCHANGE_NAME,
    task_default_exchange_type="direct",
    task_queues=(account_status_change_queue,),
)
