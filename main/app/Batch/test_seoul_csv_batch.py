import csv
import json
import tempfile
from pathlib import Path
from unittest import TestCase

from .seoul_csv_batch import (
    LOCK_FILE, MANIFEST_FILE, SourceSpec, refresh_seoul_csvs,
)


class SeoulCsvBatchTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data_dir = Path(self.directory.name) / "data"
        self.output_dir = self.data_dir / "Batch"
        self.data_dir.mkdir()
        self.spec = SourceSpec("source.csv", "CTPRVN_CD", "CTPRVN_NM")

    def _write_source(self, rows, header=("CTPRVN_CD", "CTPRVN_NM", "VALUE")):
        with (self.data_dir / self.spec.filename).open(
            "w", encoding="utf-8-sig", newline=""
        ) as output:
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)

    def _read_values(self, path):
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            return [row[-1] for row in list(csv.reader(source))[1:]]

    def test_first_run_creates_final_without_previous_file(self):
        self._write_source(
            [
                ("11", "서울", "short"),
                ("1100000000", "서울특별시", "full"),
                ("", "서울특별시", "name"),
                ("26", "부산", "other"),
            ]
        )

        result = refresh_seoul_csvs(
            self.data_dir, self.output_dir, (self.spec,)
        )[0]

        self.assertEqual(self._read_values(result.output), ["short", "full", "name"])
        self.assertEqual((result.source_rows, result.seoul_rows), (4, 3))
        self.assertFalse((self.output_dir / self.spec.previous_filename).exists())
        self.assertFalse(result.output.with_suffix(".csv.part").exists())
        manifest = json.loads(
            (self.output_dir / MANIFEST_FILE).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["files"][result.output.name]["rows"], 3)

    def test_next_run_keeps_old_final_as_temp(self):
        self._write_source([("11", "서울", "old")])
        first = refresh_seoul_csvs(
            self.data_dir, self.output_dir, (self.spec,)
        )[0]
        self._write_source([("11", "서울", "new")])

        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        previous = self.output_dir / self.spec.previous_filename
        self.assertEqual(self._read_values(first.output), ["new"])
        self.assertEqual(self._read_values(previous), ["old"])

    def test_existing_temp_is_replaced_by_the_current_final(self):
        self._write_source([("11", "서울", "first")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("11", "서울", "second")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("11", "서울", "third")])

        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        previous = self.output_dir / self.spec.previous_filename
        self.assertEqual(self._read_values(final), ["third"])
        self.assertEqual(self._read_values(previous), ["second"])
        self.assertFalse(previous.with_suffix(".csv.batch_discard").exists())

    def test_invalid_source_preserves_final_and_temp(self):
        self._write_source([("11", "서울", "first")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("11", "서울", "second")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("value",)], header=("OTHER",))

        with self.assertRaises(ValueError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        previous = self.output_dir / self.spec.previous_filename
        self.assertEqual(self._read_values(final), ["second"])
        self.assertEqual(self._read_values(previous), ["first"])
        self.assertFalse(final.with_suffix(".csv.part").exists())

    def test_zero_seoul_rows_do_not_change_existing_files(self):
        self._write_source([("11", "서울", "old")])
        refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))
        self._write_source([("26", "부산", "other")])

        with self.assertRaises(ValueError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        final = self.output_dir / self.spec.final_filename
        self.assertEqual(self._read_values(final), ["old"])

    def test_running_lock_prevents_a_second_batch(self):
        self._write_source([("11", "서울", "new")])
        self.output_dir.mkdir()
        (self.output_dir / LOCK_FILE).write_text("running", encoding="utf-8")

        with self.assertRaises(RuntimeError):
            refresh_seoul_csvs(self.data_dir, self.output_dir, (self.spec,))

        self.assertFalse((self.output_dir / self.spec.final_filename).exists())
