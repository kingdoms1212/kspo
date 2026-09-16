import json
import tempfile
import threading
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from .versioned_csv import MANIFEST_FILE, VersionedCsvCache


class VersionedCsvCacheTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data_dir = Path(self.directory.name)
        self.csv_path = self.data_dir / 'sample.csv'
        self.csv_path.write_text('old', encoding='utf-8')
        self.calls = 0

    def _loader(self):
        self.calls += 1
        return self.csv_path.read_text(encoding='utf-8')

    def _write_manifest(self, generation):
        stat = self.csv_path.stat()
        manifest = {
            'generation': generation,
            'files': {
                self.csv_path.name: {
                    'mtime_ns': stat.st_mtime_ns,
                    'size': stat.st_size,
                }
            },
        }
        (self.data_dir / MANIFEST_FILE).write_text(
            json.dumps(manifest), encoding='utf-8'
        )

    def test_same_generation_reuses_memory(self):
        self._write_manifest('one')
        cache = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir):
            self.assertEqual(cache.get(), 'old')
            self.assertEqual(cache.get(), 'old')
        self.assertEqual(self.calls, 1)

    def test_new_generation_reloads_each_process_cache(self):
        self._write_manifest('one')
        first = VersionedCsvCache(self.csv_path.name, self._loader)
        second = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir):
            self.assertEqual(first.get(), 'old')
            self.assertEqual(second.get(), 'old')
            self.csv_path.write_text('new', encoding='utf-8')
            self._write_manifest('two')
            self.assertEqual(first.get(), 'new')
            self.assertEqual(second.get(), 'new')
        self.assertEqual(self.calls, 4)

    def test_file_change_before_manifest_keeps_previous_cache(self):
        self._write_manifest('one')
        cache = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir):
            self.assertEqual(cache.get(), 'old')
            self.csv_path.write_text('new', encoding='utf-8')
            self.assertEqual(cache.get(), 'old')
        self.assertEqual(self.calls, 1)

    def test_concurrent_requests_load_new_generation_once(self):
        self._write_manifest('one')
        cache = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir):
            cache.get()
            self.csv_path.write_text('new', encoding='utf-8')
            self._write_manifest('two')
            results = []
            threads = [threading.Thread(target=lambda: results.append(cache.get())) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(results, ['new'] * 5)
        self.assertEqual(self.calls, 2)
