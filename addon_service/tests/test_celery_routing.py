from django.test import SimpleTestCase

from app.celery import app as celery_app
from app.celery import checks


class TestCeleryRouting(SimpleTestCase):
    maxDiff = None

    def setUp(self):
        # AddonServiceConfig.ready() imports celery's `include` modules like the worker does on start,
        # so the local registry has every task
        self.registered_tasks = checks.get_registered_tasks(celery_app)

    def test_every_task_has_a_route(self):
        implicit = checks.find_tasks_sent_to_default_queue_implicitly(
            celery_app, self.registered_tasks
        )
        self.assertEqual(
            implicit, [], "Tasks sent to the default queue without a route naming it"
        )

    def test_every_route_targets_a_declared_queue(self):
        undeclared = checks.find_routes_to_undeclared_queues(celery_app)
        self.assertEqual(
            undeclared, {}, "Routes to queues missing from celery's task_queues"
        )

    def test_every_route_matches_a_registered_task(self):
        unmatched = checks.find_routes_matching_no_task(
            celery_app, self.registered_tasks
        )
        self.assertEqual(unmatched, [], "Routes matching no registered task")

    def test_no_task_sets_routing_attributes(self):
        overrides = checks.find_tasks_setting_routing_attributes(self.registered_tasks)
        self.assertEqual(
            overrides,
            {},
            "Tasks setting routing attributes instead of using celery's task_routes",
        )

    def test_every_beat_schedule_entry_runs_a_registered_task(self):
        # Checked against all of celery_app.tasks
        # Entries may run celery's built-in tasks, e.g. celery.backend_cleanup
        entries = (
            (name, entry["task"])
            for name, entry in celery_app.conf.beat_schedule.items()
        )
        unregistered = checks.find_periodic_tasks_with_unregistered_task(
            celery_app, entries
        )
        self.assertEqual(
            unregistered,
            {},
            "CELERY_BEAT_SCHEDULE entries running unregistered tasks",
        )
