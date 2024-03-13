import logging
from contextlib import contextmanager

from celery import Celery
from kombu import Consumer

from addon_service.models import UserReference
from app import settings


# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@contextmanager
def consumer_connection(queues, callbacks):
    try:
        with Celery(broker=settings.OSF_BROKER_URL).connection() as connection:
            with Consumer(
                connection,
                queues=queues,
                callbacks=callbacks,
                accept=["json"],
            ) as consumer:
                yield consumer
    except Exception as e:
        logger.exception(f"An error occurred while listening on queue. Error: {e}")


@contextmanager
def handle_messaging_exceptions(message):
    """Context manager to handle message processing success and failure states."""
    try:
        yield
    except UserReference.DoesNotExist as e:
        logger.exception(f"An error occurred during message processing: {e}")
        message.reject()  # Assuming you log the error above, hence log_error=False
        raise e
    else:
        message.ack()


def process_deactivated_user_message(body, message):
    user_uri = body.get("user_uri")
    UserReference.objects.get(user_uri=user_uri).delete()
    logger.info(f"Processed and deactivated user: {user_uri}")


def process_reactivated_user_message(body, message):
    user_uri = body.get("user_uri")
    UserReference.objects.get(user_uri=user_uri).reactivate()
    logger.info(f"Processed and reactivated user: {user_uri}")


def process_merged_user_message(body, message):
    user_uri = body.get("user_uri")
    merged_user_uri = body.get("merged_user_uri")
    merged_user = UserReference.objects.get(user_uri=merged_user_uri)
    UserReference.objects.get(user_uri=user_uri).merge(merged_user)
    logger.info(f"Processed and merged user: {user_uri}")


def queue_routing_handler(body, message):
    action = body.get('action')

    with handle_messaging_exceptions(message):
        if action == 'deactivate':
            process_deactivated_user_message(body, message)
        elif action == 'reactivate':
            process_reactivated_user_message(body, message)
        elif action == 'merge':
            process_merged_user_message(body, message)
        else:
            raise NotImplementedError(f'Action {action} is not Implemented')


def listen_to_queue_route(queues):
    with consumer_connection(queues, [queue_routing_handler]) as consumer:
        while True:
            consumer.connection.drain_events()
