import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from .manual_runner import BatchAlreadyRunning, STATUS_FILE
from .regional_csv_batch import LOG_FILE, MANIFEST_FILE


class BatchTestViewTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output_dir = Path(self.directory.name)
        self.settings = override_settings(DATA_DIR=self.output_dir)
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_status_displays_manifest_and_latest_log(self):
        (self.output_dir / MANIFEST_FILE).write_text(
            json.dumps({
                "generation": "2026-09-17_0",
                "created_at": "2026-09-17T11:12:57.123456+09:00",
                "region": {"display_name": "서울"},
                "files": {
                    "public_sports_program_seoul.csv": {
                        "source_rows": 100,
                        "rows": 40,
                        "source_quality": {
                            "skipped_rows": 2,
                            "missing_region_codes": 1,
                            "invalid_region_codes": 0,
                            "region_code_mismatches": 1,
                        },
                    },
                },
            }),
            encoding="utf-8",
        )
        (self.output_dir / STATUS_FILE).write_text(
            json.dumps({
                "status": "success",
                "requested_at": "2026-09-17T11:12:57+09:00",
                "started_at": "2026-09-17T11:12:58+09:00",
                "finished_at": "2026-09-17T11:13:11+09:00",
                "progress_percent": 100,
            }),
            encoding="utf-8",
        )
        log_dir = self.output_dir / "logs"
        log_dir.mkdir()
        (log_dir / LOG_FILE).write_text(
            "2026-09-17T11:13:11+09:00 서울 CSV 배치 완료\n",
            encoding="utf-8",
        )

        response = self.client.get(reverse("batch-test-status"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-09-17_0")
        self.assertContains(response, "2026-09-17 11:12:57")
        self.assertNotContains(response, "2026-09-17T11:12:57")
        self.assertContains(response, "변경 사항 내역")
        self.assertContains(response, "원본 CSV 전체의 시군구 코드 문제")
        self.assertContains(response, "프로그램 현황")
        self.assertContains(response, '<th scope="col">코드 누락</th>')
        self.assertContains(response, '<th scope="col">코드 불일치</th>')
        self.assertNotContains(response, '&quot;generation&quot;')
        self.assertContains(response, "배치 완료")
        self.assertContains(response, 'data-batch-progress="100"')

    @patch("app.Batch.views.start_manual_batch", return_value="job-1")
    def test_post_starts_manual_batch(self, start_manual_batch):
        response = self.client.post(reverse("batch-test-run"))

        self.assertEqual(response.status_code, 202)
        start_manual_batch.assert_called_once_with()
        self.assertContains(response, "운영 데이터 최신화 작업을 시작했습니다.", status_code=202)

    @patch(
        "app.Batch.views.start_manual_batch",
        side_effect=BatchAlreadyRunning("지역 CSV 배치가 이미 실행 중입니다."),
    )
    def test_post_reports_overlapping_batch(self, start_manual_batch):
        response = self.client.post(reverse("batch-test-run"))

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "이미 실행 중입니다", status_code=409)

    def test_template_tag_renders_button_and_dialog(self):
        request = RequestFactory().get("/")
        output = Template(
            "{% load batch_tools %}{% show_batch_test_button %}"
        ).render(Context({"request": request}))

        self.assertIn("데이터 최신화 관리", output)
        self.assertIn("로그 초기화", output)
        self.assertIn('href="#i-settings"', output)
        self.assertIn('id="batch-test-dialog"', output)

    @patch("app.Batch.views.batch_is_running", return_value=False)
    def test_clear_log_empties_only_the_displayed_log(self, batch_is_running):
        log_dir = self.output_dir / "logs"
        log_dir.mkdir()
        log_path = log_dir / LOG_FILE
        log_path.write_text("이전 배치 로그\n", encoding="utf-8")
        (self.output_dir / MANIFEST_FILE).write_text(
            json.dumps({"generation": "2026-09-17_0"}),
            encoding="utf-8",
        )

        response = self.client.post(reverse("batch-test-clear-log"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "")
        self.assertContains(response, "최근 로그를 초기화했습니다.")
        self.assertContains(response, "아직 기록된 로그가 없습니다.")
        self.assertContains(response, "2026-09-17_0")
        batch_is_running.assert_called_once_with()

    @patch("app.Batch.views.batch_is_running", return_value=True)
    def test_clear_log_is_blocked_while_batch_is_running(self, batch_is_running):
        log_dir = self.output_dir / "logs"
        log_dir.mkdir()
        log_path = log_dir / LOG_FILE
        log_path.write_text("유지할 로그\n", encoding="utf-8")

        response = self.client.post(reverse("batch-test-clear-log"))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(log_path.read_text(encoding="utf-8"), "유지할 로그\n")
        self.assertContains(
            response,
            "배치 실행 중에는 로그를 초기화할 수 없습니다.",
            status_code=409,
        )
