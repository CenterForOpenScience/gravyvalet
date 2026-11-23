from datetime import timedelta
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from dj_celery_panel.conf import panel_config
from app.celery import app as celery_app
from addon_service.celery_stress_test.models import CeleryTestSuite, CeleryTestTask
from addon_service.celery_stress_test.control import cancel_suite, finish_publishing
from addon_service.celery_stress_test.metrics import suite_metrics
from addon_service.celery_stress_test.scenarios import sync_overdue_suites
from addon_service.celery_stress_test.tasks import start_celery_stress_test
from addon_service.celery_stress_test.forms import CeleryStressTestForm, WorkloadForm, CeleryScenarioForm
from addon_service.celery_stress_test.presets import PRESETS, resolve
from django.conf import settings


WorkloadFormSet = formset_factory(
    WorkloadForm,
    extra=1,
    can_delete=True,
    max_num=10,
    min_num=1,
    validate_max=True,
)


@transaction.non_atomic_requests
@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET', 'POST'])
def celery_stress_test_view(request):
    """
    Configure and start a Celery stress test.
    """
    context = panel_config.get_context(
        request,
        current_tab='celery_stress_test',
    )
    preset = request.POST.get('preset', request.GET.get('preset', 'load'))
    if preset not in PRESETS:
        return HttpResponseBadRequest('Unknown suite preset.')
    if preset != 'load':
        form = CeleryScenarioForm(request.POST if request.method == 'POST' else None,
                                  suite_type=preset, initial=PRESETS[preset]['defaults'])
        if request.method == 'POST' and form.is_valid():
            config = resolve(preset, form.cleaned_data)
            if preset == 'workflow':
                try:
                    celery_app.backend.ensure_chords_allowed()
                except (NotImplementedError, AttributeError) as exc:
                    form.add_error(None, f'This result backend does not support chords: {exc}')
            if not form.errors:
                suite = CeleryTestSuite.objects.create(
                    name=config['name'], config=config, created_by=request.user,
                    deadline_at=timezone.now() + timedelta(seconds=config['deadline_seconds']),
                )
                try:
                    start_celery_stress_test.apply_async(
                        args=[str(suite.id)], task_id=str(suite.coordinator_task_id), retry=False,
                    )
                except Exception as exc:
                    finish_publishing(suite.id, f'Coordinator publication failed: {exc}')
                    messages.error(request, 'Failed to submit the suite.')
                return redirect('celery_stress_suite_detail', suite_id=suite.id)
        context.update({'form': form, 'presets': PRESETS, 'selected_preset': preset})
        return render(request, 'admin/dj_celery_panel/scenario_testing.html', context)
    context.update({'presets': PRESETS, 'selected_preset': preset})

    if request.method == 'POST':
        form = CeleryStressTestForm(request.POST)
        workload_formset = WorkloadFormSet(request.POST)

        if form.is_valid() and workload_formset.is_valid():
            config = {
                **form.cleaned_data,
                'suite_type': 'load',
                'preset_version': 1,
                'workloads': [
                    workload_form.cleaned_data
                    for workload_form in workload_formset
                    if workload_form.cleaned_data
                    and not workload_form.cleaned_data.get('DELETE', False)
                ],
            }

            if not config['workloads']:
                messages.error(
                    request,
                    'Please configure at least one workload.',
                )
            elif config['total_duration'] * min(
                config['max_total_rate'],
                sum(workload['rate'] for workload in config['workloads']),
            ) > settings.CELERY_STRESS_TEST_MAX_TASKS:
                form.add_error(None, f'This run exceeds the {settings.CELERY_STRESS_TEST_MAX_TASKS:,} task limit.')
            else:
                suite = CeleryTestSuite.objects.create(
                    name=config['name'], config=config, created_by=request.user,
                    deadline_at=timezone.now() + timedelta(seconds=config['total_duration'] + config['drain_timeout'] + 60),
                )
                try:
                    start_celery_stress_test.apply_async(
                        args=[str(suite.id)], task_id=str(suite.coordinator_task_id), retry=False,
                    )
                except Exception as error:
                    finish_publishing(suite.id, f'Coordinator publication failed: {error}')
                    messages.error(
                        request,
                        'Failed to start the stress test. Please try again.',
                    )
                else:
                    messages.success(
                        request,
                        f"Stress test submitted successfully: {suite.name}",
                    )
                    return redirect('celery_stress_suite_detail', suite_id=suite.id)
    else:
        form = CeleryStressTestForm()
        workload_formset = WorkloadFormSet()

    context.update({
        'form': form,
        'workload_formset': workload_formset,
    })

    return render(
        request,
        'admin/dj_celery_panel/celery_stress_testing.html',
        context,
    )


@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET'])
def celery_stress_suites(request):
    """List active suites and paginate terminal runs."""
    context = panel_config.get_context(request, current_tab='celery_stress_test')
    suites = CeleryTestSuite.objects.annotate(
        task_count=Count('tasks'),
        succeeded_count=Count('tasks', filter=Q(tasks__status=CeleryTestTask.Status.SUCCEEDED)),
        failed_count=Count('tasks', filter=Q(tasks__status=CeleryTestTask.Status.FAILED)),
    ).order_by('-created_at', '-id')
    context.update({
        'active_suites': suites.filter(status__in=CeleryTestSuite.ACTIVE_STATUSES),
        'history': Paginator(suites.exclude(status__in=CeleryTestSuite.ACTIVE_STATUSES), 25).get_page(request.GET.get('page')),
    })
    return render(request, 'admin/dj_celery_panel/stress_suites.html', context)


@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET'])
def celery_stress_suite_detail(request, suite_id):
    """Show a saved suite configuration, metrics, and individual task records."""
    suite = get_object_or_404(CeleryTestSuite, pk=suite_id)
    context = panel_config.get_context(request, current_tab='celery_stress_test')
    context.update({
        'suite': suite,
        'metrics': suite_metrics(suite),
        'task_page': Paginator(suite.tasks.order_by('-submitted_at', '-id'), 50).get_page(request.GET.get('page')),
    })
    return render(request, 'admin/dj_celery_panel/stress_suite_detail.html', context)


@transaction.non_atomic_requests
@panel_config.permission_required('celery_stress_test')
@require_http_methods(['POST'])
def celery_stress_suite_cancel(request, suite_id):
    """Request cancellation and report whether broker revocation succeeded."""
    get_object_or_404(CeleryTestSuite, pk=suite_id)
    suite, warning = cancel_suite(suite_id, request.user, celery_app)
    if warning:
        messages.warning(request, warning)
    elif suite.cancel_requested_at:
        messages.success(request, 'Cancellation requested. Publishing stops; queued load tasks are revoked where possible and expire at the deadline. Running load tasks finish naturally.')
    else:
        messages.info(request, 'This suite has already finished.')
    return redirect('celery_stress_suite_detail', suite_id=suite.id)


@transaction.non_atomic_requests
@panel_config.permission_required('celery_stress_test')
@require_http_methods(['POST'])
def celery_stress_suites_sync_overdue(request):
    """Close overdue active suites from the admin dashboard."""
    sync_overdue_suites.run()
    messages.success(request, 'Checked for overdue suites and closed any that were still active.')
    return redirect('celery_stress_test')
