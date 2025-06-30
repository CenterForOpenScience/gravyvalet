from django.conf import settings
from django.contrib import admin
from django.urls import (
    include,
    path,
)
from django.views.generic.base import RedirectView


urlpatterns = [
    path("v1/", include("addon_service.urls")),
    path("admin/", admin.site.urls),
    path(
        "docs",
        RedirectView.as_view(url="/static/gravyvalet_code_docs/index.html"),
        name="docs-root",
    ),
]

if "silk" in settings.INSTALLED_APPS:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
