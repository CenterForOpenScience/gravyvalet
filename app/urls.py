from django.contrib import admin
from django.urls import (
    include,
    path,
)


urlpatterns = [
    path("v1/", include("addon_service.urls")),
    path("admin/", admin.site.urls),
]
