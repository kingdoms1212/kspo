import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from . import csv_warmup
from .versioned_csv import VersionedCsvCache


class CsvWarmupTests(SimpleTestCase):
    def test_worker_initial_load_and_single_watcher(self):
        cache = Mock()
        worker = Mock()
        with patch.object(csv_warmup, '_thread', None), \
                patch.object(csv_warmup, '_caches', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches') as warm, \
                patch.object(csv_warmup.threading, 'Thread', return_value=worker) as factory:
            csv_warmup.start_csv_warmup()
            csv_warmup.start_csv_warmup()
            warm.assert_called_once()
            factory.assert_called_once()
            worker.start.assert_called_once()
            self.assertTrue(cache.background_refresh)
            csv_warmup.stop_csv_warmup()
            self.assertFalse(cache.background_refresh)

    @override_settings(CSV_WARMUP_ENABLED=False)
    def test_disabled_does_not_read_data_or_create_thread(self):
        with patch.object(csv_warmup, 'warm_csv_caches') as warm:
            csv_warmup.start_csv_warmup()
        warm.assert_not_called()

    def test_file_created_after_startup_is_loaded_on_next_pass(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_DIR=directory):
            path = Path(directory) / 'later.csv'
            cache = VersionedCsvCache(path.name, lambda: path.read_text())
            with patch.object(csv_warmup, '_caches', return_value=(cache,)):
                csv_warmup.warm_csv_caches()
                self.assertFalse(cache._loaded)
                path.write_text('new')
                csv_warmup.warm_csv_caches()
                self.assertEqual(cache.get(), 'new')

    def test_failure_in_one_cache_does_not_block_others(self):
        bad, good = Mock(filename='bad.csv'), Mock(filename='good.csv')
        bad.get.side_effect = ValueError('bad')
        with patch.object(csv_warmup, '_caches', return_value=(bad, good)), \
                patch.object(csv_warmup, 'data_path') as path:
            path.return_value.exists.return_value = True
            with self.assertLogs('app.common.csv_warmup', level='ERROR'):
                csv_warmup.warm_csv_caches()
        good.get.assert_called_once_with(refresh=True)

    def test_watcher_polls_without_user_request_and_restores_sync_mode_on_exit(self):
        cache = Mock(background_refresh=True)
        with patch.object(csv_warmup, '_stop') as stop, \
                patch.object(csv_warmup, '_caches', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches') as warm:
            stop.wait.side_effect = [False, True]
            csv_warmup._watch(5)
            warm.assert_called_once()
            self.assertFalse(cache.background_refresh)

    def test_thread_start_failure_keeps_request_refresh_available(self):
        cache = Mock()
        with patch.object(csv_warmup, '_thread', None), \
                patch.object(csv_warmup, '_caches', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches'), \
                patch.object(csv_warmup.threading, 'Thread') as factory:
            factory.return_value.start.side_effect = RuntimeError('cannot start')
            with self.assertLogs('app.common.csv_warmup', level='ERROR'):
                csv_warmup.start_csv_warmup()
            self.assertFalse(cache.background_refresh)
