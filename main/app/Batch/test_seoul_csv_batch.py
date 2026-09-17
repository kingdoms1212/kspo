import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from app.common.regions import get_region_profile

from .regional_csv_batch import (
    LOCK_FILE, MANIFEST_FILE, SOURCE_SPECS, SourceSpec,
    refresh_region_csvs, refresh_seoul_csvs,
)


class SeoulCsvBatchTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data_dir = Path(self.directory.name) / "data"
        self.output_dir = self.data_dir / "Batch"
        self.data_dir.mkdir()
        self.spec = SourceSpec(
            "source", "source.csv",
            "CTPRVN_CD", "CTPRVN_NM", "SIGNGU_CD", "SIGNGU_NM",
        )

    def _write_source(
        self,
        rows,
        header=("CTPRVN_CD", "CTPRVN_NM", "SIGNGU_CD", "SIGNGU_NM", "VALUE"),
    ):
        with (self.data_dir / self.spec.filename).open(
            "w", encoding="utf-8-sig", newline=""
        ) as output:
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)

    def _read_values(self, path):
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            return [row[-1] for row in list(csv.reader(source))[1:]]

    def test_source_specs_use_current_english_filenames(self):
        self.assertEqual(
            {spec.key: spec.filename for spec in SOURCE_SPECS},
            {
                "programs": "public_sports_program.csv",
                "usage": "sports_voucher_usage.csv",
                "facilities": "sports_facility_status.csv",
                "transit": "facility_transit.csv",
            },
        )

    def test_first_run_creates_final_without_temp_file(self):
        self._write_source(
            [
                ("11", "서울", "11110", "종로구", "short"),
                ("1100000000", "서울특별시", "1111000000", "종로구", "full"),
                ("", "서울특별시", "1168000000", "강남구", "name"),
                ("26", "부산", "26110", "중구", "other"),
            ]
        )

        result = refresh_seoul_csvs(
            self.data_dir, self.output_dir, (self.spec,)
        )[0]

        self.assertEqual(self._read_values(result.output), ["short", "full"])
        self.assertEqual((result.source_rows, result.seoul_rows), (4, 2))
        self.assertEqual(list(self.output_dir.glob("*_temp.csv")), [])
        self.assertFalse(result.output.with_suffix(".csv.part").exists())
        manifest = json.loads(
            (self.output_dir / MANIFEST_FILE).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["files"][result.output.name]["rows"], 2)
        self.assertEqual(manifest["region"]["key"], "seoul")
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertEqual(manifest["generation"], f"{today}_0")
        self.assertNotIn("T", manifest["created_at"])
        self.assertEqual(
            manifest["files"][result.output.name]["source_quality"]["missing_region_codes"],
            1,
        )

    def test_next_run_replaces_final_without_temp_backup(self):
        self._write_source([("11", "서울", "11110", "종로구", "old")])
        first = refresh_seoul_csvs(
            self.data_dir, self.output_dir, (self.spec,)
        )[0]
        self._write_source([("11", "서울", "11110", "종로구", "new")])

        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        self.assertEqual(self._read_values(first.output), ["new"])
        self.assertEqual(list(self.output_dir.glob("*_temp.csv")), [])
        manifest = json.loads(
            (self.output_dir / MANIFEST_FILE).read_text(encoding="utf-8")
        )
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        self.assertEqual(manifest["generation"], f"{today}_1")

    def test_progress_and_elapsed_log_are_recorded(self):
        self._write_source([("11", "서울", "11110", "종로구", "new")])
        progress = []

        refresh_region_csvs(
            get_region_profile("seoul"),
            self.data_dir,
            self.output_dir,
            (self.spec,),
            progress_callback=lambda percent, message: progress.append((percent, message)),
        )

        self.assertEqual([item[0] for item in progress], [5, 70, 75, 90, 100])
        log = (self.output_dir / "logs" / "regional_batch.log").read_text(
            encoding="utf-8"
        )
        self.assertIn("서울 CSV 배치 소요 시간:", log)

    def test_existing_legacy_temp_is_deleted_after_success(self):
        self._write_source([("11", "서울", "11110", "종로구", "first")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        legacy_temp = self.output_dir / "source_seoul_temp.csv"
        legacy_temp.write_text("legacy", encoding="utf-8")
        self._write_source([("11", "서울", "11110", "종로구", "second")])

        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        self.assertEqual(self._read_values(final), ["second"])
        self.assertFalse(legacy_temp.exists())

    def test_invalid_source_preserves_final(self):
        self._write_source([("11", "서울", "11110", "종로구", "first")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("value",)], header=("OTHER",))

        with self.assertRaises(ValueError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        self.assertEqual(self._read_values(final), ["first"])
        self.assertFalse(final.with_suffix(".csv.part").exists())

    def test_zero_seoul_rows_do_not_change_existing_files(self):
        self._write_source([("11", "서울", "11110", "종로구", "old")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("26", "부산", "26110", "중구", "other")])

        with self.assertRaises(ValueError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        self.assertEqual(self._read_values(final), ["old"])

    def test_running_lock_prevents_a_second_batch(self):
        self._write_source([("11", "서울", "11110", "종로구", "new")])
        self.output_dir.mkdir()
        (self.output_dir / LOCK_FILE).write_text("running", encoding="utf-8")

        with self.assertRaises(RuntimeError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        self.assertFalse((self.output_dir / self.spec.final_filename).exists())

    def test_national_profile_keeps_all_regions(self):
        self._write_source([
            ("11", "서울", "11110", "종로구", "seoul"),
            ("26", "부산", "26110", "중구", "busan"),
        ])

        result = refresh_region_csvs(
            get_region_profile("national"),
            self.data_dir,
            self.output_dir,
            (self.spec,),
        )[0]

        self.assertEqual(result.output.name, "source_national.csv")
        self.assertEqual(self._read_values(result.output), ["seoul", "busan"])

    def test_invalid_region_codes_are_excluded_and_recorded(self):
        self._write_source([
            ("11", "서울", "11110", "종로구", "valid"),
            ("11", "서울", "", "종로구", "missing"),
            ("11", "서울", "서울", "종로구", "invalid"),
            ("11", "서울", "26110", "중구", "mismatch"),
            ("26", "부산", "", "중구", "other-region-error"),
            ("26", "부산"),
        ])

        result = refresh_seoul_csvs(
            self.data_dir, self.output_dir, (self.spec,)
        )[0]
        manifest = json.loads(
            (self.output_dir / MANIFEST_FILE).read_text(encoding="utf-8")
        )
        quality = manifest["files"][result.output.name]["source_quality"]

        self.assertEqual(self._read_values(result.output), ["valid"])
        self.assertEqual(quality["skipped_rows"], 5)
        self.assertEqual(quality["missing_region_codes"], 3)
        self.assertEqual(quality["invalid_region_codes"], 1)
        self.assertEqual(quality["region_code_mismatches"], 1)
