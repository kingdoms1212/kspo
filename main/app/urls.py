"""Compose feature routes. Each module owns its controllers."""
from django.urls import include, path

urlpatterns = [
    path("", include("app.Batch.urls")),
    path("", include("app.dashboard.urls")),
    path("", include("app.programs.urls")),
    path("", include("app.facilities.urls")),
    path("", include("app.policies.urls")),
]
