"""Exercise actual production logging in a fresh Django process."""
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class ProductionLoggingTests(SimpleTestCase):
    def test_500_traceback_is_logged_once_without_exposing_request_data(self):
        script = '''
import logging
import django
django.setup()
from django.http import HttpResponse
from django.urls import path
from django.test import Client, override_settings

def broken(request):
    raise RuntimeError("deployment-logging-probe")

urlpatterns = [path("logging-probe/", broken)]
with override_settings(ROOT_URLCONF=__name__, SECURE_SSL_REDIRECT=False):
    response = Client(raise_request_exception=False).post(
        "/logging-probe/?token=query-secret-probe",
        {"password": "body-secret-probe"},
        HTTP_AUTHORIZATION="Bearer header-secret-probe",
        HTTP_COOKIE="sessionid=cookie-secret-probe",
    )
    assert response.status_code == 500
    assert b"deployment-logging-probe" not in response.content
    assert b"Traceback" not in response.content
    print("GENERIC_500_OK")
logging.getLogger("app.Batch.scheduler").info("scheduler-info-probe")
try:
    raise ValueError("batch-error-probe")
except ValueError:
    logging.getLogger("app.Batch.scheduler").exception("batch failure")
'''
        environment = os.environ.copy()
        environment.update({
            'DJANGO_SETTINGS_MODULE': 'main.settings',
            'DEBUG': 'false',
            'SECRET_KEY': 'isolated-test-secret-not-for-deployment',
            'ALLOWED_HOSTS': 'testserver',
            'PYTHONIOENCODING': 'utf-8',
        })
        result = subprocess.run(
            [sys.executable, '-c', script], cwd=settings.BASE_DIR,
            env=environment, capture_output=True, text=True, encoding='utf-8',
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('GENERIC_500_OK', result.stdout)
        self.assertIn('ERROR django.request', result.stderr)
        self.assertIn('Internal Server Error: /logging-probe/', result.stderr)
        self.assertIn('Traceback (most recent call last)', result.stderr)
        self.assertEqual(result.stderr.count('RuntimeError: deployment-logging-probe'), 1)
        self.assertIn('scheduler-info-probe', result.stderr)
        self.assertIn('ValueError: batch-error-probe', result.stderr)
        for secret in ('query-secret-probe', 'body-secret-probe',
                       'header-secret-probe', 'cookie-secret-probe'):
            self.assertNotIn(secret, result.stderr)
