"""[SG002] - CSV파일 초기화 예외처리 화면 제공

목록 자료가 아직 없을 때 화면이 이유를 말하게 한다.

막는 경우는 둘뿐이다. 적재가 진행 중이거나(`loading`), 원본 CSV가 아예
없는(`missing`) 경우다. 감시 스레드가 없거나 너무 오래 걸리면(`stalled`)
막지 않고 통과시킨다 -- 그 경로에서는 요청이 직접 읽으므로, 막으면 아무도
적재하지 않아 화면이 영원히 안내문에 머문다.

응답 형태는 요청이 기대하는 것에 맞춘다. 전체 페이지에 안내 화면을 주는 것은
맞지만, htmx 조각 자리에 문서를 통째로 넣으면 화면이 깨지고, 설계 마법사의
JSON 호출이나 엑셀 내려받기에 HTML을 주면 오류가 엉뚱하게 보인다.
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from . import readiness

# [SG002] - CSV파일 초기화 예외처리 화면 제공
# 경로 앞부분 -> 그 화면이 필요한 목록. 값이 빈 튜플이면 자료 없이 열린다.
# 교통 상세 색인은 사전 적재 대상이 아니므로 어디에도 넣지 않는다. 넣으면
# 시설 상세를 누를 때마다 미준비로 보인다.
ROUTE_REQUIREMENTS = (
    ('/programs', ('programs',)),
    ('/export/programs', ('programs',)),
    ('/facilities', ('facilities',)),
    ('/export/facilities', ('facilities',)),
    ('/export/facility-transit', ('facilities',)),
    ('/dashboard/plan/preview', ('facilities', 'usage')),
    ('/dashboard/plan/restore', ('facilities', 'usage')),
    ('/dashboard/plan', ('facilities',)),
    ('/dashboard', ('usage',)),
)

# 자료를 읽지 않는 경로. 특히 배치 관리 화면은 적재가 안 될 때 원인을 보는
# 곳이므로 절대 막지 않는다.
# [SG002] 자료를 읽지 않는 경로. 특히 배치 관리 화면은 적재가 안 될 때 원인을 보는
# 곳이고, 개요 화면은 시스템 설명 문서다. 둘 다 자료가 없을 때야말로 열려야 한다.
EXEMPT_PREFIXES = ('/healthz', '/readyz', '/static', '/media',
                   '/policies', '/overview', '/batch-test', '/admin')

RETRY_AFTER_SECONDS = 3

LOADING_MESSAGE = '시스템 초기화 중입니다. 잠시 후 다시 시도해 주세요.'
MISSING_MESSAGE = ('서비스 데이터가 준비되지 않았습니다. '
                   '운영 데이터 최신화를 실행해 주세요.')


def required_targets(path):
    """[SG002] 이 경로가 필요한 목록 키. 해당 없으면 None."""
    for prefix, keys in ROUTE_REQUIREMENTS:
        if path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '.'):
            return keys
    return None


def _wants_json(request, path):
    """[SG002] 설계 마법사는 fetch로 JSON을 기대한다. 그 형식을 지켜야 문구가 뜬다."""
    if path.startswith('/dashboard/plan'):
        return True
    return request.headers.get('Accept', '').startswith('application/json')


class CsvReadinessMiddleware:
    """[SG002] - CSV파일 초기화 예외처리 화면 제공

    자료가 준비되기 전 요청에 이유를 담은 503을 돌려준다.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return self.get_response(request)
        keys = required_targets(path)
        if keys is None:
            return self.get_response(request)
        state = readiness.state(keys)
        # [SG002] stalled 를 막지 않는 것이 중요하다. 그 경로에서는 요청이 직접 읽으므로,
        # 막으면 아무도 적재하지 않아 화면이 영원히 안내문에 머문다.
        if state not in (readiness.LOADING, readiness.MISSING):
            return self.get_response(request)
        return self._refusal(request, path, state)

    def _refusal(self, request, path, state):
        """[SG002] 요청이 기대하는 형식으로 거절해야 화면이 깨지지 않는다."""
        message = LOADING_MESSAGE if state == readiness.LOADING else MISSING_MESSAGE
        if request.headers.get('HX-Request') == 'true':
            # 조각을 기다리는 자리에 문서를 넣지 않는다. 브라우저가 주소를 다시
            # 열게 해서 안내 화면을 온전한 페이지로 받게 한다.
            response = HttpResponse(status=503)
            response['HX-Refresh'] = 'true'
        elif _wants_json(request, path):
            response = JsonResponse({'error': message, 'state': state}, status=503)
        elif path.endswith('.xlsx'):
            response = HttpResponse(message, status=503,
                                    content_type='text/plain; charset=utf-8')
        else:
            response = render(request, 'runtime/not_ready.html', {
                'state': state,
                'message': message,
                'retry': state == readiness.LOADING,
                'retry_after': RETRY_AFTER_SECONDS,
            }, status=503)
        # 준비된 뒤에도 안내가 남지 않도록 어떤 계층에도 보관시키지 않는다.
        response['Cache-Control'] = 'no-store'
        response['Retry-After'] = str(RETRY_AFTER_SECONDS)
        return response
