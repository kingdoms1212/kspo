"""임시 기동 진단. 요청 본문·쿼리·쿠키는 기록하지 않는다."""
import logging
from time import perf_counter
from uuid import uuid4

from django.conf import settings

logger = logging.getLogger('app.runtime.diagnostics')


def trace(event, **fields):
    if getattr(settings, 'CSV_DIAGNOSTICS_ENABLED', True):
        logger.info('CSV_DIAG %s %s', event, ' '.join(
            f'{key}={value!r}' for key, value in fields.items()))


class RequestDiagnosticsMiddleware:
    """응답 완료 전에도 진입 로그를 남겨 무응답 요청을 식별한다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'CSV_DIAGNOSTICS_ENABLED', True) or request.path.startswith(('/static/', '/media/')):
            return self.get_response(request)
        request.csv_diag_id = uuid4().hex[:12]
        started = perf_counter()
        trace('request.begin', request_id=request.csv_diag_id,
              method=request.method, path=request.path)
        try:
            response = self.get_response(request)
        except Exception:
            trace('request.error', request_id=request.csv_diag_id,
                  seconds=round(perf_counter() - started, 3))
            raise
        trace('request.end', request_id=request.csv_diag_id,
              status=response.status_code, seconds=round(perf_counter() - started, 3))
        return response
