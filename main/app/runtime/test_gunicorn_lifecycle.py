"""Gunicorn preloading must not start CSV threads before workers exist."""
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings


ROOT = Path(__file__).resolve().parents[2]


class GunicornLifecycleTests(SimpleTestCase):
    @override_settings(BATCH_SCHEDULER_ENABLED=False)
    def test_preloaded_entrypoints_defer_warmup_until_worker_init(self):
        with patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()), \
                patch('app.runtime.csv_warmup.start_csv_warmup') as start, \
                patch('django.core.wsgi.get_wsgi_application'), \
                patch('django.core.asgi.get_asgi_application'):
            config = runpy.run_path(str(ROOT.parent / 'gunicorn.conf.py'))
            for entrypoint in ('wsgi.py', 'asgi.py'):
                runpy.run_path(str(ROOT / 'main' / entrypoint))
            start.assert_not_called()
            config['post_worker_init'](Mock())
            start.assert_called_once_with()

    def test_standalone_entrypoints_still_start_warmup(self):
        with patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()), \
                patch('app.runtime.csv_warmup.start_csv_warmup') as start, \
                patch('django.core.wsgi.get_wsgi_application'), \
                patch('django.core.asgi.get_asgi_application'):
            os.environ.pop('CSV_WARMUP_MANAGED_BY_GUNICORN', None)
            for entrypoint in ('wsgi.py', 'asgi.py'):
                runpy.run_path(str(ROOT / 'main' / entrypoint))
            self.assertEqual(start.call_count, 2)
