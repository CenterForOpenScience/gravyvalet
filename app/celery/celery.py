import enum
import logging

from celery import (
    Celery,
    bootsteps,
)
from celery.signals import (
    beat_init,
    worker_init,
)
from kombu import (
    Consumer,
    Queue,
)

from app.celery import checks
from app.env import (
    AMQP_BROKER_URL,
    GV_QUEUE_NAME_PREFIX,
    OSF_BACKCHANNEL_QUEUE_NAME,
)


logger = logging.getLogger(__name__)


class TaskUrgency(enum.Enum):
    INTERACTIVE = enum.auto()  # e.g. archival request from a waiting living being
    REACTIVE = enum.auto()  # e.g. account status updates
    CHILL = enum.auto()  # e.g. incremental key rotation

    def queue_name(self) -> str:
        return ".".join((GV_QUEUE_NAME_PREFIX, self.name))


gv_chill_queue = Queue(TaskUrgency.CHILL.queue_name())
gv_reactive_queue = Queue(TaskUrgency.REACTIVE.queue_name())
gv_interactive_queue = Queue(TaskUrgency.INTERACTIVE.queue_name())
osf_high_queue = Queue(
    "external_high", no_declare=True
)  # this queue must be declared by osf's celery
osf_low_queue = Queue(
    "external_low", no_declare=True
)  # this queue must be declared by osf's celery

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
        "addon_service.tasks.clear_expired_sessions.*": {"queue": gv_chill_queue},
        "addon_service.management.commands.refresh_addon_tokens.*": {
            "queue": gv_chill_queue
        },
        "osf.*": {"queue": osf_high_queue},
        "website.*": {"queue": osf_high_queue},
    },
    include=[
        "addon_service.tasks",
        "addon_service.management.commands.refresh_addon_tokens",
    ],
)

app.config_from_object("django.conf:settings", namespace="CELERY")
# Make this app the fallback for celery.current_app in every thread, not only the importing one
app.set_default()


@worker_init.connect
def check_routing(sender, **kwargs):
    """Sent once the worker has imported celery's `include` modules, so the registry has every task."""
    tasks = checks.get_registered_tasks(sender.app)
    for message, found in (
        (
            "Tasks sent to the default queue without a route naming it",
            checks.find_tasks_sent_to_default_queue_implicitly(sender.app, tasks),
        ),
        (
            "Routes to queues missing from celery's task_queues",
            checks.find_routes_to_undeclared_queues(sender.app),
        ),
        (
            "Routes matching no registered task",
            checks.find_routes_matching_no_task(sender.app, tasks),
        ),
        (
            "Tasks setting routing attributes instead of using celery's task_routes",
            checks.find_tasks_setting_routing_attributes(tasks),
        ),
    ):
        if found:
            logger.error(f"[Celery Config Check] {message}: %s", found)


@beat_init.connect
def check_periodic_tasks(sender, **kwargs):
    """Sent once beat has imported celery's `include` modules and synced CELERY_BEAT_SCHEDULE to the database,
    so the enabled PeriodicTask rows are every entry beat will run.
    """
    from django_celery_beat.models import PeriodicTask

    enabled = PeriodicTask.objects.enabled().values_list("name", "task")
    unregistered = checks.find_periodic_tasks_with_unregistered_task(
        sender.app, enabled
    )
    if unregistered:
        logger.error(
            "[Celery Config Check] Enabled periodic tasks running unregistered Celery tasks: %s",
            unregistered,
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
