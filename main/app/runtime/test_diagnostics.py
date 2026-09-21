from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from .diagnostics import RequestDiagnosticsMiddleware


@override_settings(CSV_DIAGNOSTICS_ENABLED=True)
class RequestDiagnosticsTests(SimpleTestCase):
    def test_request_pair_excludes_query_and_cookie(self):
        request = RequestFactory().get('/dashboard?secret=private', HTTP_COOKIE='token=private')
        response = HttpResponse(status=503)
        with self.assertLogs('app.runtime.diagnostics', level='INFO') as logs:
            self.assertIs(RequestDiagnosticsMiddleware(lambda req: response)(request), response)
        self.assertEqual(len(logs.output), 2)
        self.assertIn('request.begin', logs.output[0])
        self.assertIn('status=503', logs.output[1])
        self.assertTrue(all(request.csv_diag_id in line for line in logs.output))
        self.assertNotIn('private', ' '.join(logs.output))

    @override_settings(CSV_DIAGNOSTICS_ENABLED=False)
    def test_disabled_passes_through_without_logging(self):
        response = HttpResponse()
        with patch('app.runtime.diagnostics.trace') as trace:
            result = RequestDiagnosticsMiddleware(lambda req: response)(RequestFactory().get('/'))
        self.assertIs(result, response)
        trace.assert_not_called()

    def test_exception_is_not_swallowed(self):
        def fail(request):
            raise RuntimeError('test')
        with self.assertLogs('app.runtime.diagnostics', level='INFO') as logs:
            with self.assertRaises(RuntimeError):
                RequestDiagnosticsMiddleware(fail)(RequestFactory().get('/dashboard'))
        self.assertIn('request.error', logs.output[-1])
