"""웹 서버와 분리된 프로세스에서 수동 지역 배치를 실행한다."""
from django.core.management.base import BaseCommand

from app.Batch.manual_runner import _run_manual_batch


class Command(BaseCommand):
    help = "수동으로 요청한 운영 지역 CSV 배치를 실행합니다."

    def add_arguments(self, parser):
        parser.add_argument("--job-id", required=True)
        parser.add_argument("--requested-at", required=True)

    def handle(self, *args, **options):
        _run_manual_batch(options["job_id"], options["requested_at"])
