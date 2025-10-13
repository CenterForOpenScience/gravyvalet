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


urlpatterns = [
    path("v1/", include("addon_service.urls")),
    path("admin/", admin.site.urls),
    path(
        "docs",
        RedirectView.as_view(url="/static/gravyvalet_code_docs/index.html"),
        name="docs-root",
    ),
]
if settings.DEBUG:
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),

if "silk" in settings.INSTALLED_APPS:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
