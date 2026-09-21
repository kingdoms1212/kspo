import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from ..runtime import csv_warmup
from .versioned_csv import VersionedCsvCache


class CsvWarmupTests(SimpleTestCase):
    def test_compatibility_entry_points_share_one_runtime(self):
        from . import csv_warmup as legacy
        self.assertIs(legacy.start_csv_warmup, csv_warmup.start_csv_warmup)
        self.assertIs(legacy.stop_csv_warmup, csv_warmup.stop_csv_warmup)
        self.assertIs(legacy.warm_csv_caches, csv_warmup.warm_csv_caches)

    def test_registry_uses_feature_public_refresh_functions(self):
        from app.runtime.targets import csv_warmup_targets
        from app.programs import models as programs
        from app.facilities import models as facilities
        from app.dashboard import models as usage
        # 가벼운 자료부터 적재해 해당 화면이 먼저 열리게 한 순서다.
        for target, module in zip(csv_warmup_targets(), (facilities, usage, programs)):
            self.assertIs(target.refresh, module.refresh_snapshot)
            self.assertIs(target.set_background_refresh, module.set_background_refresh)
            self.assertIs(target.is_ready, module.snapshot_loaded)

    def test_startup_does_not_read_csv_before_serving_requests(self):
        """기동 호출은 스레드만 띄운다. WSGI 임포트가 적재를 기다리면 안 된다."""
        cache = Mock()
        worker = Mock()
        with patch.object(csv_warmup, '_thread', None), \
                patch.object(csv_warmup, 'csv_warmup_targets', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches') as warm, \
                patch.object(csv_warmup.threading, 'Thread', return_value=worker) as factory:
            csv_warmup.start_csv_warmup()
            csv_warmup.start_csv_warmup()
            warm.assert_not_called()
            factory.assert_called_once()
            worker.start.assert_called_once()
            cache.set_background_refresh.assert_called_with(True)
            csv_warmup.stop_csv_warmup()
            cache.set_background_refresh.assert_called_with(False)

    @override_settings(CSV_WARMUP_ENABLED=False)
    def test_disabled_does_not_read_data_or_create_thread(self):
        with patch.object(csv_warmup, 'warm_csv_caches') as warm:
            csv_warmup.start_csv_warmup()
        warm.assert_not_called()

    def test_file_created_after_startup_is_loaded_on_next_pass(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_DIR=directory):
            path = Path(directory) / 'later.csv'
            cache = VersionedCsvCache(path.name, lambda: path.read_text())
            with patch.object(csv_warmup, 'csv_warmup_targets', return_value=(cache,)):
                csv_warmup.warm_csv_caches()
                self.assertFalse(cache._loaded)
                path.write_text('new')
                csv_warmup.warm_csv_caches()
                self.assertEqual(cache.get(), 'new')

    def test_failure_in_one_cache_does_not_block_others(self):
        bad, good = Mock(filename='bad.csv'), Mock(filename='good.csv')
        bad.refresh.side_effect = ValueError('bad')
        with patch.object(csv_warmup, 'csv_warmup_targets', return_value=(bad, good)), \
                patch.object(csv_warmup, 'data_path') as path:
            path.return_value.exists.return_value = True
            with self.assertLogs('app.common.csv_warmup', level='ERROR'):
                csv_warmup.warm_csv_caches()
        good.refresh.assert_called_once_with()

    def test_watcher_polls_without_user_request_and_restores_sync_mode_on_exit(self):
        cache = Mock(background_refresh=True)
        with patch.object(csv_warmup, '_stop') as stop, \
                patch.object(csv_warmup, 'csv_warmup_targets', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches') as warm:
            stop.wait.side_effect = [False, True]
            csv_warmup._watch(5)
            # 첫 적재 한 번과 주기 한 번. 첫 적재도 이 스레드가 맡는다.
            self.assertEqual(warm.call_count, 2)
            cache.set_background_refresh.assert_called_with(False)

    def test_thread_start_failure_keeps_request_refresh_available(self):
        cache = Mock()
        with patch.object(csv_warmup, '_thread', None), \
                patch.object(csv_warmup, 'csv_warmup_targets', return_value=(cache,)), \
                patch.object(csv_warmup, 'warm_csv_caches'), \
                patch.object(csv_warmup.threading, 'Thread') as factory:
            factory.return_value.start.side_effect = RuntimeError('cannot start')
            with self.assertLogs('app.common.csv_warmup', level='ERROR'):
                csv_warmup.start_csv_warmup()
            cache.set_background_refresh.assert_called_with(False)
