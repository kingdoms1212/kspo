"""[SG002] - CSV파일 초기화 예외처리 화면 제공

준비 상태 판정과 안내 화면 게이트의 회귀 시험.
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from . import csv_warmup, readiness
from .middleware import CsvReadinessMiddleware, required_targets


def _target(key, filename, loaded):
    return Mock(key=key, label=key, filename=filename,
                is_ready=Mock(return_value=loaded))


class ReadinessStateTests(SimpleTestCase):
    """판정은 '최초 적재 여부'만 본다."""

    def _state(self, targets, keys=None, active=True, elapsed=1.0, present=True):
        with patch.object(readiness, 'csv_warmup_targets', return_value=targets), \
                patch.object(readiness, 'warmup_active', return_value=active), \
                patch.object(readiness, 'warmup_elapsed', return_value=elapsed), \
                patch.object(readiness, 'data_path') as path:
            path.return_value.exists.return_value = present
            return readiness.state(keys)

    def test_all_loaded_is_ready(self):
        targets = (_target('a', 'a.csv', True), _target('b', 'b.csv', True))
        self.assertEqual(self._state(targets), readiness.READY)

    def test_pending_while_watcher_runs_is_loading(self):
        targets = (_target('a', 'a.csv', True), _target('b', 'b.csv', False))
        self.assertEqual(self._state(targets), readiness.LOADING)

    def test_only_requested_lists_are_judged(self):
        """시설 목록이 준비되면 프로그램 적재를 기다리지 않는다."""
        targets = (_target('facilities', 'f.csv', True), _target('programs', 'p.csv', False))
        self.assertEqual(self._state(targets, ('facilities',)), readiness.READY)
        self.assertEqual(self._state(targets, ('programs',)), readiness.LOADING)

    def test_absent_source_is_missing_not_loading(self):
        """기다려도 해결되지 않는 상태는 따로 알린다."""
        targets = (_target('a', 'a.csv', False),)
        self.assertEqual(self._state(targets, present=False), readiness.MISSING)

    def test_loaded_list_survives_a_deleted_file(self):
        targets = (_target('a', 'a.csv', True),)
        self.assertEqual(self._state(targets, present=False), readiness.READY)

    def test_dead_watcher_is_stalled_so_requests_load_it_themselves(self):
        targets = (_target('a', 'a.csv', False),)
        self.assertEqual(self._state(targets, active=False), readiness.STALLED)

    def test_never_started_process_does_not_block(self):
        """관리 명령과 테스트처럼 사전 적재를 시작하지 않은 프로세스."""
        targets = (_target('a', 'a.csv', False),)
        self.assertEqual(self._state(targets, active=False, elapsed=None, present=False),
                         readiness.STALLED)

    @override_settings(CSV_READY_TIMEOUT_SECONDS=10)
    def test_overlong_load_stops_blocking(self):
        targets = (_target('a', 'a.csv', False),)
        self.assertEqual(self._state(targets, elapsed=11), readiness.STALLED)

    @override_settings(CSV_WARMUP_ENABLED=False)
    def test_disabled_warmup_never_blocks(self):
        targets = (_target('a', 'a.csv', False),)
        self.assertEqual(self._state(targets, active=False, present=False), readiness.DISABLED)

    def test_generation_refresh_keeps_ready(self):
        """배치가 새 세대를 읽는 중에도 옛 목록을 서비스하므로 준비 상태다."""
        with tempfile.TemporaryDirectory() as directory, override_settings(DATA_DIR=directory):
            from ..common.versioned_csv import VersionedCsvCache
            path = Path(directory) / 'one.csv'
            path.write_text('old', encoding='utf-8')
            cache = VersionedCsvCache(path.name, lambda: path.read_text(encoding='utf-8'))
            cache.get()
            path.write_text('new', encoding='utf-8')
            self.assertTrue(cache.is_loaded)


class ReadinessRouteTests(SimpleTestCase):
    def test_each_screen_waits_only_for_the_lists_it_reads(self):
        self.assertEqual(required_targets('/programs'), ('programs',))
        self.assertEqual(required_targets('/facilities'), ('facilities',))
        self.assertEqual(required_targets('/dashboard'), ('usage',))
        self.assertEqual(required_targets('/export/programs.xlsx'), ('programs',))
        self.assertEqual(required_targets('/dashboard/plan/facilities'), ('facilities',))
        self.assertEqual(set(required_targets('/dashboard/plan/preview')),
                         {'facilities', 'usage'})

    def test_screens_without_csv_are_never_gated(self):
        for path in ('/policies', '/batch-test/status/', '/healthz/', '/readyz/'):
            self.assertIsNone(required_targets(path))

    def test_transit_index_is_not_a_gate_condition(self):
        """교통 색인은 지연 적재다. 게이트에 넣으면 상세 클릭마다 화면이 막힌다."""
        keys = {key for _, keys in __import__(
            'app.runtime.middleware', fromlist=['ROUTE_REQUIREMENTS']
        ).ROUTE_REQUIREMENTS for key in keys}
        self.assertNotIn('transit', keys)


class ReadinessGateTests(SimpleTestCase):
    """요청이 기대하는 형식으로 거절해야 화면이 깨지지 않는다."""

    def setUp(self):
        self.called = []
        self.middleware = CsvReadinessMiddleware(lambda request: self.called.append(request) or 'passed')

    def _request(self, path, **headers):
        request = Mock(path=path, headers=headers)
        return request

    def _refuse(self, request, state=readiness.LOADING):
        with patch.object(readiness, 'state', return_value=state):
            return self.middleware(request)

    def test_ready_request_reaches_the_view(self):
        with patch.object(readiness, 'state', return_value=readiness.READY):
            self.assertEqual(self.middleware(self._request('/programs')), 'passed')

    def test_stalled_request_reaches_the_view(self):
        """막으면 아무도 적재하지 않아 화면이 영원히 안내문에 머문다."""
        self.assertEqual(self._refuse(self._request('/programs'), readiness.STALLED), 'passed')

    def test_htmx_fragment_asks_for_a_full_reload(self):
        response = self._refuse(self._request('/programs', **{'HX-Request': 'true'}))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['HX-Refresh'], 'true')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_planner_fetch_gets_json_it_can_display(self):
        response = self._refuse(self._request('/dashboard/plan/facilities'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Content-Type'], 'application/json')
        import json
        self.assertIn('초기화', json.loads(response.content)['error'])

    def test_excel_export_is_not_given_html(self):
        response = self._refuse(self._request('/export/programs.xlsx'))
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))

    def test_page_request_gets_the_notice_screen(self):
        response = self._refuse(self._request('/programs'))
        self.assertEqual(response.status_code, 503)
        body = response.content.decode()
        self.assertIn('시스템 초기화 중입니다', body)
        self.assertEqual(response['Retry-After'], '3')

    def test_absent_source_screen_does_not_invite_waiting(self):
        response = self._refuse(self._request('/programs'), readiness.MISSING)
        body = response.content.decode()
        self.assertIn('데이터가 준비되지 않았습니다', body)
        # 기다려도 해결되지 않으므로 자동 재시도 스크립트를 넣지 않는다.
        self.assertNotIn('/readyz/', body)


class HealthEndpointTests(SimpleTestCase):
    """배포 전환 시점을 정하는 경로이므로 준비 전에는 실패로 답한다."""

    def test_healthz_reports_failure_while_loading(self):
        with patch.object(readiness, 'state', return_value=readiness.LOADING):
            response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'loading'})

    def test_healthz_is_ok_once_loaded(self):
        with patch.object(readiness, 'state', return_value=readiness.READY):
            response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_readyz_lists_each_source(self):
        response = self.client.get('/readyz/')
        payload = response.json()
        self.assertIn('state', payload)
        self.assertEqual({item['key'] for item in payload['targets']},
                         {'programs', 'facilities', 'usage'})
        for item in payload['targets']:
            self.assertIn('loaded', item)
            self.assertIn('present', item)

    def test_warmup_reports_its_own_liveness(self):
        self.assertFalse(csv_warmup.warmup_active())
        self.assertIsNone(csv_warmup.warmup_elapsed())
