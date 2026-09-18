import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .versioned_csv import MANIFEST_FILE, VersionedCsvCache, DataGenerationPending
from .file_digest import sha256_file


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

    def _write_manifest(self, generation, with_hash=False):
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
        if with_hash:
            manifest['files'][self.csv_path.name]['sha256'] = sha256_file(self.csv_path)
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

    def _change_mtime(self):
        stat = self.csv_path.stat()
        os.utime(self.csv_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))

    def test_deployment_mtime_change_reads_same_content_and_hashes_only_once(self):
        self._write_manifest('one', with_hash=True)
        self._change_mtime()
        cache = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir), patch(
            'app.common.versioned_csv.sha256_file', wraps=sha256_file
        ) as digest:
            self.assertEqual(cache.get(), 'old')
            self.assertEqual(cache.get(), 'old')
            digest.assert_called_once()

    def test_changed_content_with_same_size_is_still_pending(self):
        self._write_manifest('one', with_hash=True)
        self.csv_path.write_text('new', encoding='utf-8')
        self._change_mtime()
        with override_settings(DATA_DIR=self.data_dir):
            with self.assertRaises(DataGenerationPending):
                VersionedCsvCache(self.csv_path.name, self._loader).get()

    def test_changed_file_after_hash_verification_keeps_old_cache_until_publish(self):
        self._write_manifest('one', with_hash=True)
        self._change_mtime()
        cache = VersionedCsvCache(self.csv_path.name, self._loader)
        with override_settings(DATA_DIR=self.data_dir):
            self.assertEqual(cache.get(), 'old')
            self.csv_path.write_text('new', encoding='utf-8')
            self._change_mtime()
            self.assertEqual(cache.get(), 'old')
            self._write_manifest('two', with_hash=True)
            self.assertEqual(cache.get(), 'new')

    def test_legacy_manifest_does_not_accept_unverified_mtime_change(self):
        self._write_manifest('one')
        self._change_mtime()
        with override_settings(DATA_DIR=self.data_dir):
            with self.assertRaises(DataGenerationPending):
                VersionedCsvCache(self.csv_path.name, self._loader).get()

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
