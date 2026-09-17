import json
import os
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings
from django.core.management import call_command

from . import manual_runner
from .manual_runner import BatchAlreadyRunning, STATUS_FILE, read_manual_batch_status
from .regional_csv_batch import LOCK_FILE, MANIFEST_FILE


class ManualBatchRunnerTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output_dir = Path(self.directory.name)
        self.settings = override_settings(DATA_DIR=self.output_dir, BATCH_REGION_KEY="seoul")
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_success_records_new_manifest_generation(self):
        def refresh(profile, output_dir, progress_callback):
            self.assertEqual(output_dir, self.output_dir)
            progress_callback(55, "시설 CSV 추출 완료")
            (self.output_dir / MANIFEST_FILE).write_text(
                json.dumps({"generation": "new-generation"}), encoding="utf-8"
            )

        with patch.object(manual_runner, "refresh_region_data", side_effect=refresh):
            manual_runner._run_manual_batch("job-1", "requested")

        status = read_manual_batch_status()
        self.assertEqual(status["status"], "success")
        self.assertEqual(status["generation"], "new-generation")
        self.assertEqual(status["job_id"], "job-1")
        self.assertEqual(status["progress_percent"], 100)

    def test_failure_records_error_without_hiding_it(self):
        with patch.object(
            manual_runner, "refresh_region_data", side_effect=ValueError("원본 오류")
        ):
            manual_runner._run_manual_batch("job-2", "requested")

        status = read_manual_batch_status()
        self.assertEqual(status["status"], "failed")
        self.assertIn("원본 오류", status["error"])

    def test_active_batch_lock_rejects_manual_start(self):
        (self.output_dir / LOCK_FILE).write_text("running", encoding="utf-8")

        with self.assertRaises(BatchAlreadyRunning):
            manual_runner.start_manual_batch()

    @patch.object(manual_runner.subprocess, "Popen")
    def test_start_launches_separate_management_process(self, popen):
        job_id = manual_runner.start_manual_batch()

        command = popen.call_args.args[0]
        self.assertIn("run_manual_region_batch", command)
        self.assertIn(job_id, command)
        self.assertEqual(read_manual_batch_status()["status"], "queued")

    @patch("app.management.commands.run_manual_region_batch._run_manual_batch")
    def test_management_command_runs_requested_job(self, run_manual_batch):
        call_command(
            "run_manual_region_batch",
            job_id="job-3",
            requested_at="2026-09-17 14:10:00",
            verbosity=0,
        )

        run_manual_batch.assert_called_once_with("job-3", "2026-09-17 14:10:00")

    def test_stale_running_status_is_changed_to_failed(self):
        status_path = self.output_dir / STATUS_FILE
        status_path.write_text(
            json.dumps({
                "status": "running",
                "requested_at": "2026-09-17 11:00:00",
                "progress_percent": 40,
            }),
            encoding="utf-8",
        )
        old_time = time.time() - manual_runner.STATUS_STALE_SECONDS - 1
        os.utime(status_path, (old_time, old_time))

        status = read_manual_batch_status()

        self.assertEqual(status["status"], "failed")
        self.assertIn("중단", status["error"])
