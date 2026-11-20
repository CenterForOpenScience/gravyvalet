"""Checks of the celery routing and beat schedule, which the signal handlers in app.celery.celery report to Sentry when a worker or beat starts.

They run against the settings of the environment the process starts in, which the tests in
addon_service/tests/test_celery_routing.py don't see: e.g. a deployment's environment variables or the periodic tasks stored in the database.
"""

from fnmatch import fnmatchcase

from kombu import Queue


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


def get_registered_tasks(app):
    return {
        name: task for name, task in app.tasks.items() if not name.startswith("celery.")
    }


def find_tasks_sent_to_default_queue_implicitly(app, tasks):
    # Celery silently sends a task to task_default_queue when no route matches it or its matching route
    # is empty or names no queue, so a task may only end up there when its route names that queue
    default_queue = app.conf.task_default_queue
    router = app.amqp.router
    implicit = []
    for name, task in sorted(tasks.items()):
        # Resolve the queue like Task.apply_async() does: the task's own options merged over its route
        queue = router.route(dict(task._get_exec_options()), name).get("queue")
        route = router.lookup_route(name) or {}
        if (queue is None or queue.name == default_queue) and _queue_name(
            route.get("queue")
        ) != default_queue:
            implicit.append(name)
    return implicit


def find_routes_to_undeclared_queues(app):
    # A queue missing from task_queues is created on send (task_create_missing_queues), with no worker consuming it
    declared = {queue.name for queue in app.conf.task_queues}
    return {
        entry: _queue_name(route.get("queue"))
        for entry, route in app.conf.task_routes.items()
        if not _routes_to_osf_queue(route)
        and _queue_name(route.get("queue")) not in declared
    }


def find_routes_matching_no_task(app, tasks):
    # Celery matches task_routes entries against task names as fnmatch globs, so an entry that
    # matches no registered task routes nothing: the task is gone, renamed, or not in celery's `include`
    return [
        entry
        for entry, route in app.conf.task_routes.items()
        if not _routes_to_osf_queue(route)
        and not any(fnmatchcase(name, entry) for name in tasks)
    ]


def find_tasks_setting_routing_attributes(tasks):
    # Only catches routing set on the task decorator (e.g. @shared_task(queue=...)). Overrides passed at call time,
    # e.g. task.apply_async(queue=...), live in the calling code and take precedence over both, but aren't visible here
    overrides = {}
    for name, task in sorted(tasks.items()):
        attributes = {
            attr: getattr(task, attr)
            for attr in ROUTING_ATTRIBUTES
            if getattr(task, attr, None) is not None
        }
        if attributes:
            overrides[name] = attributes
    return overrides


def find_periodic_tasks_with_unregistered_task(app, periodic_tasks):
    # periodic_tasks are (entry name, task name) pairs, e.g. from CELERY_BEAT_SCHEDULE or the database.
    # Beat sends tasks by name, so otherwise an unregistered one is only noticed when a worker discards it
    return {name: task for name, task in periodic_tasks if task not in app.tasks}
