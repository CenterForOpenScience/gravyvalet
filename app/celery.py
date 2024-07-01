import enum

from celery import (
    Celery,
    bootsteps,
)
from kombu import (
    Consumer,
    Queue,
)

from app.env import (
    AMQP_BROKER_URL,
    GV_QUEUE_NAME_PREFIX,
    OSF_BACKCHANNEL_QUEUE_NAME,
)


class TaskUrgency(enum.Enum):
    INTERACTIVE = enum.auto()  # e.g. archival request from a waiting living being
    REACTIVE = enum.auto()  # e.g. account status updates
    CHILL = enum.auto()  # e.g. incremental key rotation

    def queue_name(self) -> str:
        return ".".join((GV_QUEUE_NAME_PREFIX, self.name))


gv_chill_queue = Queue(TaskUrgency.CHILL.queue_name())
gv_reactive_queue = Queue(TaskUrgency.REACTIVE.queue_name())
gv_interactive_queue = Queue(TaskUrgency.INTERACTIVE.queue_name())


app = Celery(
    broker_url=AMQP_BROKER_URL,
    task_queues=(
        gv_interactive_queue,
        gv_reactive_queue,
        gv_chill_queue,
    ),
    task_routes={
        "addon_service.tasks.invocation.*": {"queue": gv_interactive_queue},
        "addon_service.tasks.osf_backchannel.*": {"queue": gv_reactive_queue},
        "addon_service.tasks.key_rotation.*": {"queue": gv_chill_queue},
    },
    include=["addon_service.tasks"],
)


###
# additional consumer for custom (non-celery) messages from osf


class OsfBackchannelConsumerStep(bootsteps.ConsumerStep):
    def get_consumers(self, channel):
        from addon_service.tasks import osf_backchannel

        def _enqueue_handler_task(body, message):
            osf_backchannel.get_handler_signature(body).delay()
            message.ack()

        return [
            Consumer(
                channel,
                queues=[Queue(OSF_BACKCHANNEL_QUEUE_NAME)],
                callbacks=[_enqueue_handler_task],
                accept=["json"],
            ),
        ]


# app.steps["consumer"].add(OsfBackchannelConsumerStep)
