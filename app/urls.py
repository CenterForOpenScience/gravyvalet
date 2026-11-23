from django.conf import settings
from django.contrib import admin
from django.urls import (
    include,
    path,
)
from django.views.generic.base import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from addon_service.celery_stress_test import views as stress_test_views


urlpatterns = [
    path("v1/", include("addon_service.urls")),
    path(
        "admin/dj-celery-panel/celery_stress_test/",
        stress_test_views.celery_stress_suites,
        name="celery_stress_test",
    ),
    path(
        "admin/dj-celery-panel/celery_stress_test/sync-overdue/",
        stress_test_views.celery_stress_suites_sync_overdue,
        name="celery_stress_suites_sync_overdue",
    ),
    path(
        "admin/dj-celery-panel/celery_stress_test/new/",
        stress_test_views.celery_stress_test_view,
        name="celery_stress_test_new",
    ),
    path(
        "admin/dj-celery-panel/celery_stress_test/<uuid:suite_id>/",
        stress_test_views.celery_stress_suite_detail,
        name="celery_stress_suite_detail",
    ),
    path(
        "admin/dj-celery-panel/celery_stress_test/<uuid:suite_id>/cancel/",
        stress_test_views.celery_stress_suite_cancel,
        name="celery_stress_suite_cancel",
    ),
    path("admin/dj-celery-panel/", include("dj_celery_panel.urls")),
    path("admin/", admin.site.urls),
    path(
        "docs",
        RedirectView.as_view(url="/static/gravyvalet_code_docs/index.html"),
        name="docs-root",
    ),
]
if settings.DEBUG:
    urlpatterns.append(
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    )
    urlpatterns.append(
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    )
    urlpatterns.append(
        path(
            "api/schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    )

if "silk" in settings.INSTALLED_APPS:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
