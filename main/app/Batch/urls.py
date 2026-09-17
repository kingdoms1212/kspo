"""운영 데이터 수동 최신화 화면의 경로를 관리한다."""
from django.urls import path

from . import views


urlpatterns = [
    path("batch-test/status/", views.batch_test_status, name="batch-test-status"),
    path("batch-test/run/", views.batch_test_run, name="batch-test-run"),
    path(
        "batch-test/clear-log/",
        views.batch_test_clear_log,
        name="batch-test-clear-log",
    ),
]
