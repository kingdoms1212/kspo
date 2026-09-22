"""프로젝트 개요 화면 회귀 시험."""
from unittest.mock import patch

from django.test import SimpleTestCase

from ..runtime import readiness
from ..runtime.middleware import EXEMPT_PREFIXES, required_targets


class OverviewScreenTests(SimpleTestCase):
    def test_screen_opens_with_the_document_sections(self):
        body = self.client.get('/overview').content.decode()
        for anchor in ('ov-summary', 'ov-tree', 'ov-pipeline', 'ov-arch',
                       'ov-ui', 'ov-libs', 'ov-guards'):
            self.assertIn(f'id="{anchor}"', body)

    def test_document_loads_no_external_font_or_script_host(self):
        """화면은 CDN에 닿지 못하는 폐쇄망에서도 떠야 한다."""
        body = self.client.get('/overview').content.decode()
        for host in ('fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.jsdelivr.net',
                     'cdnjs.cloudflare.com', 'unpkg.com'):
            self.assertNotIn(host, body)

    def test_integrated_document_keeps_diagrams_without_print_control(self):
        body = self.client.get('/overview').content.decode()
        for identifier in ('architecture-map-title', 'exception-map-title',
                           'ov-domain', 'ov-api', 'ov-limits', 'ov-evidence'):
            self.assertIn(f'id="{identifier}"', body)
        self.assertIn('project-overview.js', body)
        self.assertNotIn('id="print-document"', body)
        self.assertNotIn('인쇄 / PDF 저장', body)
        self.assertNotIn('data:font/ttf', body)

    def test_screen_reads_no_csv_snapshot(self):
        """저장소를 부르면 자료가 없을 때 이 문서까지 못 읽게 된다."""
        with patch('app.programs.models.programs') as programs, \
                patch('app.facilities.models.facilities') as facilities, \
                patch('app.dashboard.models.usage_snapshot') as usage:
            self.assertEqual(self.client.get('/overview').status_code, 200)
        programs.assert_not_called()
        facilities.assert_not_called()
        usage.assert_not_called()


class OverviewSidebarTests(SimpleTestCase):
    def test_button_sits_in_every_screen_sidebar(self):
        for path in ('/dashboard', '/programs', '/facilities'):
            with self.subTest(path=path):
                body = self.client.get(path).content.decode()
                self.assertIn('class="overview-launch"', body)
                self.assertIn('href="/overview"', body)

    def test_button_marks_itself_current_only_on_its_own_screen(self):
        overview = self.client.get('/overview').content.decode()
        self.assertIn('href="/overview"\n     aria-current="page"', overview)
        dashboard = self.client.get('/dashboard').content.decode()
        self.assertNotIn('href="/overview"\n     aria-current="page"', dashboard)


class OverviewReadinessTests(SimpleTestCase):
    """자료가 없을 때야말로 읽혀야 하는 문서이므로 준비 상태 게이트에서 제외한다."""

    def test_route_waits_for_no_csv_list(self):
        self.assertIsNone(required_targets('/overview'))

    def test_route_is_exempt_from_the_gate(self):
        self.assertIn('/overview', EXEMPT_PREFIXES)

    def test_screen_opens_while_lists_are_missing(self):
        with patch.object(readiness, 'state', return_value=readiness.MISSING):
            self.assertEqual(self.client.get('/overview').status_code, 200)
