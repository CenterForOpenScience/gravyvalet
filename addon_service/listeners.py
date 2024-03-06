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
    """Context manager to handle consumer connections and exceptions."""
    logger.info(f"Starting to listen on queue")
    try:
        with Celery(broker=settings.OSF_BROKER_URL).connection() as connection:
            with Consumer(
                connection,
                queues=queues,
                callbacks=callbacks,
                accept=["json"],
            ) as consumer:
                logger.info("Consumer set up successfully. Waiting for messages...")
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
        raise  # Optional: re-raise exception if you want calling code to handle it
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
    routing_key = message.delivery_info["routing_key"]

    with handle_messaging_exceptions(message):
        if routing_key == settings.DEACTIVATED_ROUTING_KEY:
            process_deactivated_user_message(body, message)
        elif routing_key == settings.REACTIVATED_ROUTING_KEY:
            process_reactivated_user_message(body, message)
        elif routing_key == settings.MERGED_ROUTING_KEY:
            process_merged_user_message(body, message)
        else:
            raise NotImplementedError()


def listen_to_queue_route(queue_routes):
    logger.info("Starting to listen for deactivated user signals...")
    with consumer_connection(queue_routes, [queue_routing_handler]) as consumer:
        while True:
            consumer.connection.drain_events()
