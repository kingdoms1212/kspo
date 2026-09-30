# 서정길 [SJG001] 전체 아키텍처·공통 처리 — 백엔드 계층 구성
"""Compose feature routes. Each module owns its controllers."""
from django.urls import include, path

urlpatterns = [
    path("", include("app.Batch.urls")),
    path("", include("app.dashboard.urls")),
    path("", include("app.programs.urls")),
    path("", include("app.facilities.urls")),
    path("", include("app.policies.urls")),
    path("", include("app.overview.urls")),
]
