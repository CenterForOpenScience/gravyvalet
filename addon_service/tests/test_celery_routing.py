from fnmatch import fnmatchcase

from django.test import SimpleTestCase
from kombu import Queue

from app.celery import app as celery_app


# Set on the task itself (e.g. @shared_task(queue=...)), these take precedence over task_routes
ROUTING_ATTRIBUTES = ("queue", "exchange", "routing_key")


def _queue_name(queue):
    # task_routes entries may give a queue by name or as a kombu Queue
    return queue.name if isinstance(queue, Queue) else queue


def _routes_to_osf_queue(route):
    # Queues with no_declare=True are declared and consumed by osf's celery. They carry the osf tasks
    # sent by name with send_task(), which are never registered here
    queue = route.get("queue")
    return isinstance(queue, Queue) and queue.no_declare


class TestCeleryRouting(SimpleTestCase):
    maxDiff = None

    def setUp(self):
        # AddonServiceConfig.ready() imports celery's `include` modules like the worker does on start,
        # so the local registry has every task
        self.registered_tasks = {
            name: task
            for name, task in celery_app.tasks.items()
            if not name.startswith("celery.")
        }

    def test_every_task_has_a_route(self):
        # Celery silently sends a task to task_default_queue when no route matches it or its matching route
        # is empty or names no queue, so a task may only end up there when its route names that queue
        default_queue = celery_app.conf.task_default_queue
        router = celery_app.amqp.router
        implicit = []
        for name, task in sorted(self.registered_tasks.items()):
            # Resolve the queue like Task.apply_async() does: the task's own options merged over its route
            queue = router.route(dict(task._get_exec_options()), name).get("queue")
            route = router.lookup_route(name) or {}
            if (queue is None or queue.name == default_queue) and _queue_name(
                route.get("queue")
            ) != default_queue:
                implicit.append(name)
        self.assertEqual(
            implicit, [], "Tasks sent to the default queue without a route naming it"
        )

    def test_every_route_targets_a_declared_queue(self):
        # A queue missing from task_queues is created on send (task_create_missing_queues), with no worker consuming it
        declared = {queue.name for queue in celery_app.conf.task_queues}
        undeclared = {
            entry: _queue_name(route.get("queue"))
            for entry, route in celery_app.conf.task_routes.items()
            if not _routes_to_osf_queue(route)
            and _queue_name(route.get("queue")) not in declared
        }
        self.assertEqual(
            undeclared, {}, "Routes to queues missing from celery's task_queues"
        )

    def test_every_route_matches_a_registered_task(self):
        # Celery matches task_routes entries against task names as fnmatch globs, so an entry that
        # matches no registered task routes nothing: the task is gone, renamed, or not in celery's `include`
        unmatched = [
            entry
            for entry, route in celery_app.conf.task_routes.items()
            if not _routes_to_osf_queue(route)
            and not any(fnmatchcase(name, entry) for name in self.registered_tasks)
        ]
        self.assertEqual(unmatched, [], "Routes matching no registered task")

    def test_no_task_sets_routing_attributes(self):
        # Only catches routing set on the task decorator (e.g. @shared_task(queue=...)). Overrides passed at call time,
        # e.g. task.apply_async(queue=...), live in the calling code and take precedence over both, but aren't visible here
        overrides = {}
        for name, task in sorted(self.registered_tasks.items()):
            attributes = {
                attr: getattr(task, attr)
                for attr in ROUTING_ATTRIBUTES
                if getattr(task, attr, None) is not None
            }
            if attributes:
                overrides[name] = attributes
        self.assertEqual(
            overrides,
            {},
            "Tasks setting routing attributes instead of using celery's task_routes",
        )
