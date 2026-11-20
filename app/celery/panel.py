from collections import defaultdict
from fnmatch import fnmatchcase

from dj_celery_panel.celery_utils import (
    CeleryQueuesInspectBackend,
    QueueDetailPage,
    QueueListPage,
)


class RoutedTasksQueuesBackend(CeleryQueuesInspectBackend):
    """dj-celery-panel queues backend that also lists the tasks routed to each queue, the
    task_routes entries that match no task, and the configured queues that no active worker consumes.

    Routes are resolved the same way Celery does when sending a task, so explicit
    queue= overrides passed to apply_async() at call time are not reflected.
    """

    BACKEND_DESCRIPTION = "Queue bindings, routing configuration, routed tasks, unmatched routing entries and unconsumed queues"

    def get_queues(self):
        page = super().get_queues()
        # Workers report only the queues they consume, so a configured queue nobody consumes
        # would be missing from the list while tasks routed to it pile up
        listed = {queue["name"] for queue in page.queues}
        unconsumed = [
            self.describe_unconsumed_queue(queue)
            for name, queue in sorted(self.app.amqp.queues.items())
            if name not in listed
        ]
        routed_tasks = self.get_routed_tasks_by_queue()
        unmatched_entries = self.get_unmatched_routing_entries_by_queue()
        return QueueListPage(
            queues=[
                {
                    **queue,
                    "routed_tasks_count": len(routed_tasks[queue["name"]]),
                    "unmatched_routing_entries": unmatched_entries[queue["name"]],
                }
                for queue in page.queues + unconsumed
            ],
            error=page.error,
        )

    def get_queue_detail(self, queue_name):
        page = super().get_queue_detail(queue_name)
        queue = page.queue
        if queue is None:
            # membership check first: indexing Queues creates missing ones
            if queue_name not in self.app.amqp.queues:
                return page
            queue = self.describe_unconsumed_queue(self.app.amqp.queues[queue_name])
        return QueueDetailPage(
            queue={**queue, "routed_tasks": self.get_routed_tasks(queue_name)},
            error=page.error,
        )

    def describe_unconsumed_queue(self, queue):
        broker_info = self._get_queue_length_from_broker(queue.name)
        return {
            "name": queue.name,
            "exchange": queue.exchange.name,
            "exchange_type": queue.exchange.type,
            "routing_key": queue.routing_key,
            "durable": queue.durable,
            "auto_delete": queue.auto_delete,
            "exclusive": queue.exclusive,
            "arguments": queue.queue_arguments,
            "workers": [],
            "worker_details": [],
            "message_count": broker_info.get("length"),
            "consumer_count": broker_info.get("consumer_count"),
            "broker_query_error": broker_info.get("error"),
        }

    def get_routed_tasks(self, queue_name):
        return self.get_routed_tasks_by_queue()[queue_name]

    def get_registered_tasks(self):
        # AddonServiceConfig.ready() imports every task module, so the local registry is complete
        return {
            name: task
            for name, task in self.app.tasks.items()
            if not name.startswith("celery.")
        }

    def get_routed_tasks_by_queue(self):
        router = self.app.amqp.router
        routed_tasks = defaultdict(list)
        for name, task in sorted(self.get_registered_tasks().items()):
            options = dict(task._get_exec_options())
            routed_tasks[router.route(options, name)["queue"].name].append(name)
        return routed_tasks

    def get_unmatched_routing_entries_by_queue(self):
        # Celery matches task_routes entries against task names as fnmatch globs, so an entry
        # that matches no registered task name routes nothing: the task is gone, renamed,
        # or its module isn't in the celery app's include.
        # Entries routed to queues outside task_queues (osf.*, website.*) are for OSF tasks
        # sent by name with send_task(), which are never registered here, so they are skipped
        task_names = self.get_registered_tasks()
        router = self.app.amqp.router
        unmatched_entries = defaultdict(list)
        for entry, route in sorted(self.app.conf.task_routes.items()):
            queue_name = router.expand_destination(dict(route))["queue"].name
            if queue_name in self.app.amqp.queues and not any(
                fnmatchcase(name, entry) for name in task_names
            ):
                unmatched_entries[queue_name].append(entry)
        return unmatched_entries
