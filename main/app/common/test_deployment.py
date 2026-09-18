"""Deployment regressions: host policy, HTTPS, and source archive layout."""
import importlib.util
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from app.Batch.regional_csv_batch import SOURCE_SPECS
from app.management.commands.prepare_render_data import unpack_sources


class DeploymentTests(SimpleTestCase):
    def load_settings(self, environment):
        spec = importlib.util.spec_from_file_location(
            'deployment_settings', settings.BASE_DIR / 'main' / 'settings.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, environment, clear=True):
            spec.loader.exec_module(module)
        return module

    def test_render_host_and_https_configuration(self):
        config = self.load_settings({
            'RENDER': 'true', 'SECRET_KEY': 'test-only-key',
            'RENDER_EXTERNAL_HOSTNAME': 'example.onrender.com',
            'ALLOWED_HOSTS': 'example.org, www.example.org',
            'CSRF_TRUSTED_ORIGINS': 'https://example.org',
        })
        self.assertFalse(config.DEBUG)
        self.assertEqual(config.ALLOWED_HOSTS,
                         ['example.org', 'www.example.org', 'example.onrender.com'])
        self.assertIn('https://example.onrender.com', config.CSRF_TRUSTED_ORIGINS)
        self.assertTrue(config.CSRF_COOKIE_SECURE)
        self.assertEqual(config.SECURE_PROXY_SSL_HEADER,
                         ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_render_without_secret_fails(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load_settings({'RENDER': 'true'})

    def test_local_development_still_works(self):
        config = self.load_settings({})
        self.assertTrue(config.DEBUG)
        self.assertIn('127.0.0.1', config.ALLOWED_HOSTS)

    @override_settings(SECURE_SSL_REDIRECT=True,
                       SECURE_REDIRECT_EXEMPT=[r'^healthz/$'])
    def test_health_check_does_not_redirect_or_read_csv(self):
        self.assertEqual(self.client.get('/healthz/').json(), {'status': 'ok'})

    def test_archive_extracts_only_expected_csvs_and_replaces_stale_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'origin.zip'
            output = root / 'data'
            output.mkdir()
            (output / SOURCE_SPECS[0].filename).write_text('stale')
            with ZipFile(archive_path, 'w') as archive:
                for spec in SOURCE_SPECS:
                    archive.writestr(f'origin/{spec.filename}', 'header\nnew\n')
                archive.writestr('../unexpected.txt', 'do not extract')
            unpack_sources(archive_path, output, overwrite=True)
            self.assertFalse((root / 'unexpected.txt').exists())
            for spec in SOURCE_SPECS:
                self.assertEqual((output / spec.filename).read_text(), 'header\nnew\n')

    def test_incomplete_archive_fails_before_replacing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'origin.zip'
            with ZipFile(archive_path, 'w') as archive:
                archive.writestr(f'origin/{SOURCE_SPECS[0].filename}', 'partial')
            with self.assertRaises(CommandError):
                unpack_sources(archive_path, root / 'data')
            self.assertFalse((root / 'data').exists())

    def test_existing_sources_need_no_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for spec in SOURCE_SPECS:
                (root / spec.filename).write_text('keep')
            self.assertEqual(unpack_sources(root / 'missing.zip', root), [])
            for spec in SOURCE_SPECS:
                self.assertEqual((root / spec.filename).read_text(), 'keep')

    def test_only_missing_or_empty_csvs_are_extracted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / SOURCE_SPECS[0].filename).write_text('keep')
            (root / SOURCE_SPECS[1].filename).write_text('')
            archive_path = root / 'origin.zip'
            with ZipFile(archive_path, 'w') as archive:
                for spec in SOURCE_SPECS[1:]:
                    archive.writestr(f'origin/{spec.filename}', 'restored')
            extracted = unpack_sources(archive_path, root)
            self.assertEqual(len(extracted), 3)
            self.assertEqual((root / SOURCE_SPECS[0].filename).read_text(), 'keep')
            for spec in SOURCE_SPECS[1:]:
                self.assertEqual((root / spec.filename).read_text(), 'restored')
