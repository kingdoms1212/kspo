"""Partial-rendering contract for the screens that swap a region.

The programs screen does not take part: it reloads in full and restores the
reader's scroll position from a hidden `_scroll` field instead, because its map
initialises once per page load. See docs/DECISIONS.md.
"""
import json
import re
from unittest.mock import patch

from django.test import SimpleTestCase

from . import crawler

from ..facilities.tests import REPORT as FACILITY_REPORT, facility
from ..programs.tests import REPORT as PROGRAM_REPORT, program

HX = {'HTTP_HX_REQUEST': 'true'}
RESTORE = {'HTTP_HX_REQUEST': 'true', 'HTTP_HX_HISTORY_RESTORE_REQUEST': 'true'}

DASHBOARD = {'areas': [], 'months': [], 'ledger_rows': 0, 'unidentified': 0, 'source': 'x.csv'}


class FragmentRenderingTests(SimpleTestCase):
    """An htmx request returns only the swapped region, never the page chrome."""

    def _screens(self):
        return (
            ('/dashboard', 'dashboard/index.html', 'dashboard/_body.html', 'dashboard-body'),
            ('/facilities', 'facilities/index.html', 'facilities/_workspace.html', 'facility-workspace'),
        )

    def _patches(self):
        return (
            patch('app.dashboard.models.usage_snapshot', return_value=DASHBOARD),
            patch('app.programs.models.programs', return_value=[program()]),
            patch('app.programs.models.load_report', return_value=PROGRAM_REPORT),
            patch('app.facilities.views.models.facilities', return_value=[facility()]),
            patch('app.facilities.views.models.load_report', return_value=FACILITY_REPORT),
            patch('app.facilities.views.facility_transit', return_value=None),
        )

    def test_navigation_renders_the_shell_and_htmx_renders_only_the_fragment(self):
        for route, page, fragment, container in self._screens():
            with self.subTest(route=route):
                for patcher in self._patches():
                    self.enterContext(patcher)
                full = self.client.get(route)
                partial = self.client.get(route, **HX)
                self.assertTemplateUsed(full, page)
                self.assertTemplateUsed(full, fragment)
                self.assertTemplateUsed(partial, fragment)
                self.assertTemplateNotUsed(partial, page)
                self.assertTemplateNotUsed(partial, 'base.html')
                # The container stays in the document; only its contents are replaced.
                self.assertContains(full, f'id="{container}"')
                self.assertNotContains(partial, f'id="{container}"')
                self.assertNotContains(partial, '<nav aria-label="주 메뉴">')
                self.assertNotContains(partial, 'htmx.min.js')

    def test_fragment_keeps_the_same_data_as_the_full_page(self):
        for patcher in self._patches():
            self.enterContext(patcher)
        full = self.client.get('/facilities', {'region': '서울특별시'})
        partial = self.client.get('/facilities', {'region': '서울특별시'}, **HX)
        self.assertEqual(len(full.context['rows']), len(partial.context['rows']))
        self.assertIn('시설 목록', partial.content.decode())

    def test_pagination_links_target_the_fragment_container(self):
        rows = [facility(id=f'facility-{index}', name=f'시설 {index:02}') for index in range(23)]
        with patch('app.facilities.views.models.facilities', return_value=rows), \
             patch('app.facilities.views.models.load_report', return_value=FACILITY_REPORT), \
             patch('app.facilities.views.facility_transit', return_value=None):
            response = self.client.get('/facilities')
        body = response.content.decode()
        self.assertIn('hx-target="#facility-workspace"', body)
        self.assertIn('hx-swap="innerHTML show:none"', body)
        self.assertIn('hx-get="?region=&amp;industry=', body)
        # Every htmx link keeps a real href so the page still works without JS.
        self.assertIn('href="?region=&amp;industry=', body)

    def test_the_programs_screen_reloads_in_full_and_restores_scroll(self):
        """Programs opted out of swapping: its map initialises once per page load."""
        with patch('app.programs.models.programs', return_value=[program()]), \
             patch('app.programs.models.load_report', return_value=PROGRAM_REPORT):
            response = self.client.get('/programs', {'_scroll': '640'})
        body = response.content.decode()
        self.assertNotIn('hx-target="#program-results"', body)
        self.assertIn('id="program-scroll-position"', body)
        self.assertIn('value="640"', body)


    def test_history_restore_returns_the_whole_page_not_a_fragment(self):
        """Back and forward re-request the URL with HX-Request still set.

        htmx swaps that answer into the body, so a fragment would strip the
        page down to one component.
        """
        for route, page, fragment, container in self._screens():
            with self.subTest(route=route):
                for patcher in self._patches():
                    self.enterContext(patcher)
                restored = self.client.get(route, **RESTORE)
                self.assertTemplateUsed(restored, page)
                self.assertTemplateUsed(restored, 'base.html')
                self.assertContains(restored, f'id="{container}"')
                self.assertContains(restored, '<nav aria-label="주 메뉴">')
                self.assertContains(restored, 'htmx.min.js')
                self.assertNotContains(restored, 'hx-swap-oob')

    def test_history_restore_matches_a_plain_navigation_byte_for_byte(self):
        for patcher in self._patches():
            self.enterContext(patcher)
        query = {'region': '서울특별시', 'page': 1}
        navigated = self.client.get('/facilities', query)
        restored = self.client.get('/facilities', query, **RESTORE)
        self.assertEqual(restored.content, navigated.content)

    def test_swapped_controls_carry_stable_focus_keys(self):
        rows = [facility(id=f'facility-{index}', name=f'시설 {index:02}') for index in range(23)]
        with patch('app.facilities.views.models.facilities', return_value=rows),              patch('app.facilities.views.models.load_report', return_value=FACILITY_REPORT),              patch('app.facilities.views.facility_transit', return_value=None):
            first = self.client.get('/facilities')
            second = self.client.get('/facilities', {'page': 2}, **HX)
        # The key survives the swap, so focus can return to the same control.
        self.assertIn('data-focus-key="#facility-workspace-next"', first.content.decode())
        self.assertIn('data-focus-key="#facility-workspace-prev"', second.content.decode())
        # A focusable fallback exists for the last page, where next disappears.
        self.assertIn('data-focus-fallback', second.content.decode())

    def test_dashboard_heading_updates_out_of_band_only_in_a_fragment(self):
        with patch('app.dashboard.models.usage_snapshot', return_value=DASHBOARD):
            full = self.client.get('/dashboard')
            partial = self.client.get('/dashboard', **HX)
        self.assertNotContains(full, 'hx-swap-oob')
        self.assertContains(partial, 'hx-swap-oob="true"')
        self.assertEqual(full.content.decode().count('id="dashboard-heading"'), 1)


class RegionMapComponentTests(SimpleTestCase):
    """Both screens declare the shared map, and its data must be valid JSON.

    An absent context variable makes `json_script` emit `""`. That used to
    silently kill the map after a merge, so both JSON shapes are asserted here.
    """

    MAPS = (
        ('/dashboard', 'dashboard-region-map', 'emit'),
        ('/programs', 'program-region-map', 'drilldown'),
    )

    def _patches(self):
        return (
            patch('app.dashboard.models.usage_snapshot', return_value=DASHBOARD),
            patch('app.programs.models.programs', return_value=[program()]),
            patch('app.programs.models.load_report', return_value=PROGRAM_REPORT),
        )

    def test_every_screen_declares_a_map_the_shared_script_can_find(self):
        for route, map_id, click in self.MAPS:
            with self.subTest(route=route):
                for patcher in self._patches():
                    self.enterContext(patcher)
                response = self.client.get(route)
                body = response.content.decode()
                self.assertIn(f'id="{map_id}"', body)
                self.assertIn('data-region-map', body)
                self.assertIn(f'data-region-source="{map_id}-region-data"', body)
                self.assertIn(f'data-district-source="{map_id}-district-data"', body)
                self.assertIn(f'data-region-click="{click}"', body)
                self.assertIn('region-map.js', body)

    def test_map_data_blocks_have_the_shapes_the_renderer_expects(self):
        for route, map_id, _ in self.MAPS:
            with self.subTest(route=route):
                for patcher in self._patches():
                    self.enterContext(patcher)
                body = self.client.get(route).content.decode()
                for suffix, expected_type in (('region-data', list), ('district-data', dict)):
                    block = re.search(
                        rf'<script id="{map_id}-{suffix}"[^>]*>(.*?)</script>', body, re.S)
                    self.assertIsNotNone(block, f'{map_id}-{suffix} 누락')
                    self.assertIsInstance(json.loads(block.group(1)), expected_type)

    def test_only_one_copy_of_the_drawing_script_is_loaded(self):
        for patcher in self._patches():
            self.enterContext(patcher)
        for route, _, _ in self.MAPS:
            with self.subTest(route=route):
                body = self.client.get(route).content.decode()
                self.assertEqual(body.count('src="/static/region-map.js'), 1)

    def test_each_screen_loads_only_its_own_map_adapter(self):
        for patcher in self._patches():
            self.enterContext(patcher)
        dashboard = self.client.get('/dashboard').content.decode()
        programs = self.client.get('/programs').content.decode()
        self.assertIn('dashboard-region-map.js', dashboard)
        self.assertNotIn('programs-region-map.js', dashboard)
        self.assertIn('programs-region-map.js', programs)
        self.assertNotIn('dashboard-region-map.js', programs)

    def test_a_screen_without_a_map_does_not_load_the_script(self):
        with patch('app.facilities.views.models.facilities', return_value=[facility()]), \
             patch('app.facilities.views.models.load_report', return_value=FACILITY_REPORT), \
             patch('app.facilities.views.facility_transit', return_value=None):
            body = self.client.get('/facilities').content.decode()
        self.assertNotIn('region-map.js', body)
        self.assertNotIn('data-region-map', body)


SOURCE = {
    'name': '테스트 목록',
    'base_url': 'https://example.test/site/policy/',
    'list_path': 'list.jsp?pType=07',
    'table_class': 'board',
    'cell_class': 'tit_wrap',
    'limit': 3,
    'timeout': 1,
    'cache_seconds': 900,
    'retry_seconds': 60,
    'max_bytes': 1000,
    'user_agent': 'test',
}

LISTING = """
<table class="notice"><tr><td class="tit_wrap"><a href="other.jsp" title="다른 표">X</a></td></tr></table>
<table class="board list">
  <tr>
    <td class="num">1</td>
    <td class="tit_wrap"><a href="view.jsp?pSeq=1&amp;pType=07" title="첫 번째 정책"><p>첫 번째 정책</p></a></td>
  </tr>
  <tr><td class="tit_wrap"><a href="view.jsp?pSeq=2" title="두 번째 정책">두 번째</a></td></tr>
  <tr><td class="tit_wrap"><a href="view.jsp?pSeq=3" title="세 번째 정책">세 번째</a></td></tr>
  <tr><td class="tit_wrap"><a href="view.jsp?pSeq=4" title="네 번째 정책">네 번째</a></td></tr>
</table>
"""


class ListingCrawlerTests(SimpleTestCase):
    """The shared crawler reads any listing described by a source mapping."""

    def test_reads_titles_and_resolves_relative_links(self):
        items = crawler.parse_links(LISTING, SOURCE)
        self.assertEqual([item['title'] for item in items],
                         ['첫 번째 정책', '두 번째 정책', '세 번째 정책'])
        self.assertEqual(items[0]['url'], 'https://example.test/site/policy/view.jsp?pSeq=1&pType=07')

    def test_limit_comes_from_the_source_setting(self):
        self.assertEqual(len(crawler.parse_links(LISTING, SOURCE)), 3)
        self.assertEqual(len(crawler.parse_links(LISTING, {**SOURCE, 'limit': 10})), 4)

    def test_only_the_configured_table_is_read(self):
        titles = [item['title'] for item in crawler.parse_links(LISTING, {**SOURCE, 'limit': 10})]
        self.assertNotIn('다른 표', titles)

    def test_a_missing_table_yields_nothing_rather_than_guessing(self):
        self.assertEqual(crawler.parse_links('<table class="other"><td class="tit_wrap">'
                                             '<a href="x" title="t">a</a></td></table>', SOURCE), [])

    def test_links_leaving_the_source_host_are_dropped(self):
        markup = ('<table class="board"><tr><td class="tit_wrap">'
                  '<a href="https://elsewhere.test/x" title="외부">a</a>'
                  '<a href="javascript:alert(1)" title="스크립트">b</a>'
                  '<a href="view.jsp?pSeq=9" title="정상">c</a>'
                  '</td></tr></table>')
        self.assertEqual([i['title'] for i in crawler.parse_links(markup, SOURCE)], ['정상'])

    def test_anchor_without_a_title_or_href_is_skipped(self):
        markup = ('<table class="board"><tr><td class="tit_wrap">'
                  '<a href="view.jsp?pSeq=1">제목 없음</a><a title="주소 없음">x</a>'
                  '</td></tr></table>')
        self.assertEqual(crawler.parse_links(markup, SOURCE), [])

    def test_list_url_joins_base_and_path(self):
        self.assertEqual(crawler.list_url(SOURCE), 'https://example.test/site/policy/list.jsp?pType=07')

    def test_a_failed_fetch_reports_instead_of_raising(self):
        with patch('app.common.crawler.fetch', return_value=('', crawler.NETWORK_ERROR)):
            self.assertEqual(crawler.crawl(SOURCE), ([], crawler.NETWORK_ERROR))

    def test_changed_markup_reports_instead_of_showing_nothing(self):
        with patch('app.common.crawler.fetch', return_value=('<table class="other"></table>', '')):
            self.assertEqual(crawler.crawl(SOURCE), ([], crawler.MARKUP_ERROR))

    def test_a_network_exception_becomes_a_message(self):
        with patch('app.common.crawler.urlopen', side_effect=OSError('boom')):
            self.assertEqual(crawler.fetch(SOURCE), ('', crawler.NETWORK_ERROR))

    def test_a_non_http_source_is_refused_before_any_request(self):
        with patch('app.common.crawler.urlopen') as opener:
            markup, error = crawler.fetch({**SOURCE, 'base_url': 'file:///etc/', 'list_path': 'passwd'})
        opener.assert_not_called()
        self.assertEqual((markup, error), ('', crawler.NETWORK_ERROR))
