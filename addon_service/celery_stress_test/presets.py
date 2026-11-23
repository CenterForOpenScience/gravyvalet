"""Versioned, server-owned defaults; each run stores its resolved configuration."""
from copy import deepcopy

from django.conf import settings

PRESETS = {
    'load': {'label': 'Custom load test', 'version': 1, 'defaults': {}},
    'retry': {'label': 'Retry and recovery', 'version': 2,
              'defaults': {'queue': settings.CELERY_STRESS_TEST_DEFAULT_QUEUE, 'tasks_per_scenario': 1, 'transient_failures': 2, 'retry_delay': 2, 'max_retries': 3, 'deadline_seconds': 120}},
    'workflow': {'label': 'Workflow correctness', 'version': 2,
                 'defaults': {'queue': settings.CELERY_STRESS_TEST_DEFAULT_QUEUE, 'workflow_count': 1, 'chain_length': 2, 'group_size': 3, 'chord_size': 3, 'deadline_seconds': 120}},
}


def resolve(preset, overrides):
    """Merge submitted values with preset defaults and record the preset version."""
    definition = PRESETS[preset]
    return {**deepcopy(definition['defaults']), **overrides,
            'suite_type': preset, 'preset_version': definition['version']}
