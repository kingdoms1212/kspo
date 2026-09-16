"""Dashboard controller and repository boundary tests."""
import csv
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.template.loader import render_to_string
from django.urls import resolve

from . import models, views
from .services import (
    courses_per_facility, dashboard_data, normalized_chart_rows,
    district_distribution, requests_per_course, requests_per_facility, requests_per_sport, pie_chart_data,
)


def area(**overrides):
    row = dict(region='서울', district='중구', facilities=2, courses=5, requests=100,
               sports=Counter({'수영': 100}), first_month='2025-01', last_month='2025-06')
    row.update(overrides)
    return row


class DashboardServiceTests(SimpleTestCase):
    def test_district_choices_are_sorted_and_independent_of_selected_district(self):
        snapshot = dict(areas=[area(district='중구'), area(district='강남구', requests=None),
                              area(district='종로구'), area(region='부산', district='중구')],
                        months=[], ledger_rows=4, unidentified=0, source='x.csv')
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            data = dashboard_data('서울', '중구')
        self.assertEqual(data['region_district_options']['서울'], ['강남구', '종로구', '중구'])
        self.assertNotIn('부산', data['region_district_options'])
        self.assertEqual(len(data['areas']), 1)

    def setUp(self):
        self.areas = [area(), area(district='종로구', facilities=1, courses=2, requests=0,
                                   sports=Counter({'축구': 0})),
                      area(region='부산', district='중구', facilities=3, courses=7, requests=50,
                           sports=Counter({'수영': 50}))]
        self.snapshot = {'areas': self.areas, 'months': ['2025-01', '2025-06'],
                         'ledger_rows': 9, 'unidentified': 1, 'source': 'x.csv'}

    def test_region_filter_sums_districts_and_preserves_zero(self):
        with patch('app.dashboard.models.usage_snapshot', return_value=self.snapshot):
            result = dashboard_data('서울')
        self.assertEqual(len(result['areas']), 2)
        self.assertEqual(result['facilities'], 3)
        self.assertEqual(result['courses'], 7)
        self.assertEqual(result['requests'], 100)
        self.assertEqual(result['sports'], [('수영', 100), ('축구', 0)])

    def test_sport_totals_follow_the_selected_region(self):
        with patch('app.dashboard.models.usage_snapshot', return_value=self.snapshot):
            self.assertEqual(dashboard_data()['sports'], [('수영', 100), ('축구', 0)])
            self.assertEqual(dashboard_data('부산')['sports'], [('수영', 100), ('축구', 0)])

    def test_district_distribution_groups_every_region(self):
        self.assertEqual(district_distribution(self.areas), {
            '부산': [('중구', 50)],
            '서울': [('중구', 100), ('종로구', 0)],
        })

    def test_ratios_require_a_known_positive_denominator(self):
        self.assertEqual(courses_per_facility(2, 5), 2.5)
        self.assertIsNone(courses_per_facility(0, 5))
        self.assertIsNone(requests_per_course(5, None))
        self.assertIsNone(courses_per_facility(-1, 5))
        self.assertIsNone(requests_per_course(-1, 5))
        self.assertEqual(requests_per_sport(2, 100), 50)
        self.assertEqual(requests_per_sport(2, 0), 0)
        for count, requests in [(0, 100), (None, 100), (2, None)]:
            self.assertIsNone(requests_per_sport(count, requests))
        self.assertEqual(requests_per_facility(4, 100), 25)
        self.assertEqual(requests_per_facility(4, 0), 0)
        for facilities, requests in [(0, 100), (-1, 100), (None, 100), (4, None)]:
            self.assertIsNone(requests_per_facility(facilities, requests))

    def test_all_sports_and_their_counts_follow_the_region_filter(self):
        seoul = [dict(name=f'종목{i}', facilities=1, courses=2, requests=i)
                 for i in range(7)]
        busan = [dict(name='종목0', facilities=3, courses=4, requests=10)]
        self.snapshot['areas'] = [
            area(sports=Counter({row['name']: row['requests'] for row in seoul}),
                 sport_details=seoul),
            area(region='부산', sports=Counter({'종목0': 10}), sport_details=busan),
        ]
        with patch('app.dashboard.models.usage_snapshot', return_value=self.snapshot):
            national = dashboard_data()
            selected = dashboard_data('서울')
            empty = dashboard_data('없는 지역')
        self.assertEqual(len(national['sport_rows']), 7)
        self.assertEqual(national['sport_count'], 7)
        self.assertEqual(national['sport_rows'][0],
                         dict(name='종목0', facilities=1, courses=2, requests=0))
        self.assertEqual(selected['sport_rows'][0], seoul[0])
        self.assertEqual(empty['sport_rows'], seoul)


class DashboardChartTests(SimpleTestCase):
    def test_pie_geometry_colors_and_print_rank_are_independent_of_list_order(self):
        rows = [dict(name=f'sport{i}', requests=i) for i in range(12)]
        ascending = pie_chart_data(normalized_chart_rows(rows, 'asc'))
        descending = pie_chart_data(normalized_chart_rows(rows, 'desc'))
        self.assertEqual(ascending['gradient'], descending['gradient'])
        self.assertEqual(ascending['rows'][0]['requests'], 0)
        self.assertEqual(descending['rows'][0]['requests'], 11)
        for left, right in zip(ascending['rows'], reversed(descending['rows'])):
            self.assertEqual((left['path'], left['color'], left['number']), (right['path'], right['color'], right['number']))
        markup = render_to_string('dashboard/_pie.html', dict(pie=ascending, label='test'))
        self.assertEqual(markup.count('class="db-print-omit"'), 2)
        self.assertEqual(sum(row['number'] <= 10 for row in ascending['rows']), 10)

    def test_pie_uses_actual_totals_and_handles_missing_zero_data(self):
        rows = [dict(requests=10), dict(requests=30), dict(requests=0), dict(requests=None)]
        pie = pie_chart_data(rows)
        self.assertEqual(pie['total'], 40)
        self.assertEqual([row['share'] for row in pie['rows']], [25, 75, 0, 0])
        self.assertNotIn('share', rows[0])
        self.assertIn('100.00000000%', pie['gradient'])
        self.assertEqual(pie_chart_data(rows[2:])['gradient'], 'none')

    def test_min_max_normalization_sorting_and_cache_immutability(self):
        rows = [dict(name=name, requests=value)
                for name, value in [('중간', 30), ('최대', 50), ('최소', 10), ('누락', None)]]
        ascending = normalized_chart_rows(rows, 'asc')
        descending = normalized_chart_rows(rows, 'desc')
        self.assertEqual([row['requests'] for row in ascending], [10, 30, 50, None])
        self.assertEqual([row['bar_percent'] for row in ascending], [0, 50, 100, None])
        self.assertEqual([row['requests'] for row in descending], [50, 30, 10, None])
        self.assertEqual([row['bar_percent'] for row in descending], [100, 50, 0, None])
        self.assertEqual([row['requests'] for row in rows], [30, 50, 10, None])
        self.assertTrue(all('bar_percent' not in row for row in rows))
        self.assertEqual(normalized_chart_rows(rows, 'invalid'), descending)

    def test_empty_missing_zero_and_constant_series(self):
        self.assertEqual(normalized_chart_rows([]), [])
        for value, expected in [(None, None), (0, 0), (7, 100)]:
            with self.subTest(value=value):
                rows = normalized_chart_rows([dict(requests=value), dict(requests=value)])
                self.assertEqual([row['bar_percent'] for row in rows], [expected, expected])


class DashboardRepositoryTests(SimpleTestCase):
    BASE = ('11', '서울', '11680', '강남구', '테스트시설', '서울시 강남구 1', '2층',
            '수영', '900', '2025', '03', '4')

    def _load(self, rows):
        models.usage_snapshot.cache_clear()
        self.addCleanup(models.usage_snapshot.cache_clear)
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory) / models.USAGE_FILE).open('w', encoding='utf-8-sig', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(models.COLUMNS)
                writer.writerows(rows)
            with override_settings(DATA_DIR=directory):
                return models.usage_snapshot()

    def test_distinct_facilities_and_courses_are_counted_once_per_district(self):
        second_month = list(self.BASE)
        second_month[models.ESTBL_MT] = '04'
        other_course = list(self.BASE)
        other_course[models.COURSE_NO] = '901'
        snapshot = self._load([self.BASE, second_month, other_course])
        self.assertEqual(len(snapshot['areas']), 1)
        found = snapshot['areas'][0]
        self.assertEqual(found['facilities'], 1)
        self.assertEqual(found['courses'], 2)
        self.assertEqual(found['requests'], 12)
        self.assertEqual((found['first_month'], found['last_month']), ('2025-03', '2025-04'))

    def test_filters_source_region_column_and_normalizes_seoul_aliases(self):
        rows = []
        for region in ('서울', '서울시', '서울특별시', '부산', ''):
            row = list(self.BASE)
            row[models.CTPRVN_NM] = region
            rows.append(row)
        snapshot = self._load(rows)
        self.assertEqual(snapshot['ledger_rows'], 3)
        self.assertEqual(len(snapshot['areas']), 1)
        self.assertEqual(snapshot['areas'][0]['region'], '서울')
        self.assertEqual(snapshot['areas'][0]['requests'], 12)
        self.assertEqual(snapshot['areas'][0]['facilities'], 1)

    def test_incomplete_identity_is_excluded_and_reported(self):
        nameless = list(self.BASE)
        nameless[models.FCLTY_NM] = ''
        snapshot = self._load([self.BASE, nameless])
        self.assertEqual(snapshot['unidentified'], 1)
        self.assertEqual(snapshot['ledger_rows'], 2)
        self.assertEqual(snapshot['areas'][0]['facilities'], 1)

    def test_unknown_month_is_not_recorded_as_a_period(self):
        broken = list(self.BASE)
        broken[models.ESTBL_MT] = '13'
        snapshot = self._load([broken])
        self.assertEqual(snapshot['months'], [])
        self.assertEqual(snapshot['areas'][0]['first_month'], '')

    def test_sport_counts_deduplicate_months_and_include_each_offered_sport(self):
        next_month = list(self.BASE)
        next_month[models.ESTBL_MT] = '04'
        other_course = list(self.BASE)
        other_course[models.COURSE_NO] = '901'
        other_sport = list(self.BASE)
        other_sport[models.ITEM_NM] = '축구'
        other_sport[models.COURSE_NO] = '902'
        snapshot = self._load([self.BASE, next_month, other_course, other_sport])
        found = snapshot['areas'][0]
        sports = {row['name']: row for row in found['sport_details']}
        self.assertEqual(found['facilities'], 1)
        self.assertEqual(found['courses'], 3)
        self.assertEqual(sports['수영'], dict(name='수영', facilities=1, courses=2, requests=12))
        self.assertEqual(sports['축구'], dict(name='축구', facilities=1, courses=1, requests=4))

    def test_sports_with_missing_and_zero_requests_remain_distinct(self):
        missing = list(self.BASE)
        missing[models.REQST_CO] = ''
        missing[models.ITEM_NM] = ''
        zero = list(self.BASE)
        zero[models.REQST_CO] = '0'
        snapshot = self._load([missing, zero])
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            rows = {row['name']: row for row in dashboard_data()['sport_rows']}
        self.assertIsNone(rows['종목 미제공']['requests'])
        self.assertEqual(rows['종목 미제공']['facilities'], 1)
        self.assertEqual(rows['수영']['requests'], 0)


class DashboardViewTests(SimpleTestCase):
    def test_visible_region_controls_and_metrics_follow_map_in_same_layout(self):
        context = dict(region_options=['서울'], region_district_options={'서울': ['강남구', '중구']})
        with patch('app.dashboard.views.dashboard_data', return_value=context):
            response = self.client.get('/dashboard', {'region': '서울', 'district': '강남구'})
        self.assertEqual(response.context['district_options'], ['강남구', '중구'])
        self.assertContains(response, 'data-remove-district="강남구"')
        self.assertContains(response, '지역 선택')
        self.assertContains(response, '선택한 행정구역')
        self.assertNotContains(response, '<select hidden')
        html = response.content.decode()
        self.assertLess(html.index('class="panel map-panel"'), html.index('class="db-metrics"'))

    def test_district_selection_filters_counts_and_preserves_map_scope(self):
        from urllib.parse import parse_qs, urlsplit

        snapshot = dict(areas=[area(), area(district='종로구', requests=40),
                              area(region='부산', requests=200)],
                        months=[], ledger_rows=3, unidentified=0, source='x.csv')
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            response = self.client.get('/dashboard', {'region': '서울', 'district': '중구', 'chart_type': 'pie'})
            no_region = self.client.get('/dashboard', {'district': '중구'})
        self.assertEqual(response.context['requests'], 100)
        self.assertEqual(len(response.context['areas']), 1)
        self.assertEqual(len(response.context['district_distribution']), 1)
        self.assertEqual(parse_qs(urlsplit(response.context['sport_sort_url']).query)['district'], ['중구'])
        self.assertEqual(no_region.context['selected_district'], '중구')
        self.assertEqual(no_region.context['requests'], 100)

    def test_new_layout_renders_all_sports_with_counts_and_normalized_bars(self):
        sports = [dict(name=f'종목{i}', facilities=1, courses=2, requests=i * 10)
                  for i in range(7)]
        context = dict(areas=[area()], sport_rows=sports, facilities=2, courses=5,
                       requests=100, region_options=['서울'])
        with patch('app.dashboard.views.dashboard_data', return_value=context):
            response = self.client.get('/dashboard')
        self.assertContains(response, '<h1>프로그램 설계</h1>', html=True)
        self.assertContains(response, '종목 수')
        self.assertNotContains(response, 'db-sport-count')
        self.assertContains(response, '종목6')
        self.assertContains(response, '시설 1개')
        self.assertContains(response, '강좌 2건')
        self.assertContains(response, 'conic-gradient(')
        self.assertNotContains(response, 'class="db-chart-table"')
        self.assertContains(response, '시설당 신청인원')
        self.assertNotContains(response, '관측 개설 인원')
        self.assertNotContains(response, 'db-region-filter')
        self.assertNotContains(response, 'db-source')
        self.assertNotContains(response, 'db-chart-scale')
        self.assertContains(response, 'class="db-sort-toggle"', count=2)
        self.assertContains(response, 'class="metric-icon"', count=4)
        self.assertNotContains(response, '상위 5')
        self.assertNotContains(response, '자료상 신청인원')
        self.assertContains(response, 'region-picker')
        self.assertEqual(response.content.decode().count('name="region"'), 1)
        self.assertNotContains(response, 'data-legend-position')

    def test_fragment_preserves_all_filters_and_history_restores_full_page(self):
        from html.parser import HTMLParser

        class SelectedOptions(HTMLParser):
            def __init__(self):
                super().__init__()
                self.name = None
                self.selected = {}

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'select':
                    self.name = attrs.get('name')
                elif tag == 'input' and attrs.get('type') == 'hidden':
                    self.selected[attrs['name']] = attrs.get('value')
                elif tag == 'option' and 'selected' in attrs:
                    self.selected[self.name] = attrs.get('value')

        query = '/dashboard?region=서울&region_sort=asc&sport_sort=desc'
        with patch('app.dashboard.views.dashboard_data', return_value={'region_options': ['서울']}):
            full = self.client.get(query)
            partial = self.client.get(query, HTTP_HX_REQUEST='true')
            restored = self.client.get(query, HTTP_HX_REQUEST='true', HTTP_HX_HISTORY_RESTORE_REQUEST='true')
        parser = SelectedOptions()
        parser.feed(partial.content.decode())
        self.assertEqual(parser.selected, dict(region='서울', district='', region_sort='asc', sport_sort='desc'))
        self.assertContains(partial, 'hx-trigger="submit"')
        self.assertNotContains(partial, 'id="dashboard-body"')
        self.assertNotContains(partial, 'region-map.js')
        # CSRF masks are freshly randomized on each full-page response.
        import re
        normalize = lambda body: re.sub(rb'name="csrfmiddlewaretoken" value="[^"]+"', b'name="csrfmiddlewaretoken"', body)
        self.assertEqual(normalize(full.content), normalize(restored.content))

    def test_shared_map_retains_original_markup_without_legend_override(self):
        context = dict(id='test-map', region_data=[], district_data=[], value_label='신청인원')
        markup = render_to_string('components/region_map.html', context)
        self.assertNotIn('data-legend-position', markup)
        self.assertIn('data-region-map', markup)

    def test_both_chart_shapes_render_and_sort_preserves_region(self):
        from urllib.parse import parse_qs, urlsplit

        context = dict(areas=[area()], sport_rows=[dict(name='수영', requests=100, facilities=2, courses=5)])
        with patch('app.dashboard.views.dashboard_data', return_value=context):
            pie = self.client.get('/dashboard', {'chart_type': 'pie', 'region': '서울', 'region_sort': 'asc'},
                                  HTTP_HX_REQUEST='true')
            bar = self.client.get('/dashboard', {'chart_type': 'invalid'})
        self.assertContains(pie, 'conic-gradient(', count=2)
        self.assertContains(pie, '100명')
        self.assertNotContains(pie, 'class="db-chart-table"')
        self.assertNotIn('chart_type', parse_qs(urlsplit(pie.context['region_sort_url']).query))
        self.assertContains(bar, 'conic-gradient(', count=2)
        html = pie.content.decode()
        self.assertEqual(html.count('class="db-pie-panel"'), 2)
        self.assertNotContains(bar, 'class="db-chart-table"')

    def test_tooltips_and_map_helper_use_the_existing_icon_button(self):
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard')
        self.assertNotContains(response, '<details class="db-help">')
        self.assertContains(response, 'class="heading-help"', count=9)
        self.assertContains(response, 'class="db-helper"')
        self.assertContains(response, 'role="tooltip"', count=9)

    def test_sort_parameters_and_fourth_policy_metric(self):
        context = dict(areas=[area(requests=10), area(district='종로구', requests=30)],
                       facilities=2, courses=4, requests=40,
                       sport_rows=[dict(name='수영', requests=30), dict(name='축구', requests=10)])
        with patch('app.dashboard.views.dashboard_data', return_value=context):
            response = self.client.get('/dashboard?region=서울&region_sort=asc&sport_sort=asc')
        self.assertEqual(response.context['selected_region'], '서울')
        self.assertEqual([row['requests'] for row in response.context['region_chart_rows']], [10, 30])
        self.assertEqual([row['requests'] for row in response.context['sport_chart_rows']], [10, 30])
        self.assertEqual(response.context['requests_per_facility'], 20)
        self.assertNotIn('observed_people', response.context)

    def test_default_region_and_invalid_sort(self):
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard?region_sort=wrong&sport_sort=wrong')
        self.assertEqual(response.context['selected_region'], '서울')
        self.assertEqual(response.context['region_sort'], 'desc')
        self.assertEqual(response.context['sport_sort'], 'desc')

    def test_sort_links_toggle_only_the_requested_chart(self):
        from urllib.parse import parse_qs, urlsplit

        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard',
                                       {'region': '전남광주', 'region_sort': 'asc', 'sport_sort': 'desc'})
            region_url = response.context['region_sort_url']
            sport_url = response.context['sport_sort_url']
            changed = self.client.get('/dashboard' + region_url, HTTP_HX_REQUEST='true')
        self.assertEqual(parse_qs(urlsplit(region_url).query),
                         dict(region=['서울'], region_sort=['desc'], sport_sort=['desc']))
        self.assertEqual(parse_qs(urlsplit(sport_url).query),
                         dict(region=['서울'], region_sort=['asc'], sport_sort=['asc']))
        self.assertEqual(changed.context['region_sort'], 'desc')
        self.assertContains(changed, 'hx-params="none"', count=2)

    def test_multi_district_totals_selection_and_layout(self):
        from bs4 import BeautifulSoup
        from urllib.parse import parse_qs, urlsplit
        rows = [area(district=name, requests=count,
                     sport_details=[dict(name='수영', facilities=1, courses=2, requests=count)])
                for name, count in [('강남구', 10), ('중구', 20), ('종로구', 90)]]
        snapshot = dict(areas=rows, months=[], ledger_rows=3, unidentified=0, source='x.csv')
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            response = self.client.get('/dashboard', {'district': ['중구', '강남구', '중구']}, HTTP_HX_REQUEST='true')
            all_response = self.client.get('/dashboard')
        self.assertEqual(response.context['requests'], 30)
        self.assertEqual(response.context['region_pie']['total'], 30)
        self.assertEqual(response.context['sport_pie']['total'], 30)
        self.assertEqual(response.context['facilities'], 4)
        self.assertEqual(response.context['sport_count'], 1)
        self.assertEqual(all_response.context['requests'], 120)
        self.assertEqual(parse_qs(urlsplit(response.context['sport_sort_url']).query)['district'], ['강남구,중구'])
        page = BeautifulSoup(response.content, 'html.parser')
        self.assertEqual([b['data-remove-district'] for b in page.select('.db-selected-chip')], ['강남구', '중구'])
        columns = page.select_one('.db-region-workspace').find_all(recursive=False)
        self.assertEqual([c.get('class')[0] for c in columns], ['db-region-map-column', 'db-region-choices', 'db-selected-column', 'db-map-actions'])
        self.assertEqual(len(page.select('.db-charts .db-pie-panel')), 2)
        self.assertFalse(page.select('.db-chart-table'))
        self.assertIsNotNone(page.select_one('.db-plan-action #plan-start'))
        html = response.content.decode()
        self.assertLess(html.index('class="panel map-panel"'), html.index('class="db-metrics"'))
        self.assertLess(html.index('class="db-metrics"'), html.index('class="db-charts"'))
        self.assertLess(html.index('class="panel db-policy"'), html.index('id="plan-start"'))

    def test_step_header_region_layout_and_removed_copy(self):
        from bs4 import BeautifulSoup
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard')
        page = BeautifulSoup(response.content, 'html.parser')
        steps = page.select('.planner-steps li')
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0].get_text(' ', strip=True), 'STEP 01 지역 선택')
        self.assertEqual(page.select_one('.db-scope h2').text, '시설 이용현황')
        self.assertEqual(page.select_one('.db-selection-all').text, '행정구역을 선택해주세요')
        self.assertIsNotNone(page.select_one('.db-region-map-column .section-title h2 + .db-helper'))
        for selector in ('#dashboard-region-map-level', '#dashboard-region-map-help', '.map-panel .unit', '.plan-insight', '#plan-start-help'):
            self.assertIsNone(page.select_one(selector))

    def test_seoul_controls_and_policy_order(self):
        context = dict(region_options=['서울'], region_district_options={'서울': ['강남구', '중구']},
                       facilities=2, courses=4, requests=40, sport_count=2)
        with patch('app.dashboard.views.dashboard_data', return_value=context) as data:
            response = self.client.get('/dashboard?region=부산')
        data.assert_called_once_with('서울')
        self.assertEqual(response.context['requests_per_sport'], 20)
        self.assertNotContains(response, '전국 보기')
        self.assertNotContains(response, '수혜율')
        self.assertContains(response, 'data-district="강남구"')
        from bs4 import BeautifulSoup
        page = BeautifulSoup(response.content, 'html.parser')
        panel = page.select_one('.map-panel')
        self.assertEqual(panel.select_one('.db-region-workspace').find_all(recursive=False)[-1].get('class'), ['db-map-actions'])
        self.assertEqual([b.text for b in panel.select('.db-map-actions button')], ['초기화', '조회'])
        labels = [label.get_text(strip=True) for label in page.select('.db-policy-label')]
        self.assertEqual(labels, ['시설당 강좌', '강좌당 신청인원', '시설당 신청인원', '종목당 신청인원'])

    def test_module_route_and_template(self):
        self.assertIs(resolve('/dashboard').func, views.dashboard)
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard')
        self.assertTemplateUsed(response, 'dashboard/index.html')

    def test_page_reports_usage_counts_and_new_policy_metric(self):
        snapshot = {'areas': [area(requests=0), area(district='종로구', requests=None)],
                    'months': ['2025-01'], 'ledger_rows': 4, 'unidentified': 0, 'source': 'x.csv'}
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            response = self.client.get('/dashboard')
        self.assertEqual(response.context['region_chart_max'], 0)
        self.assertContains(response, '0명')
        self.assertContains(response, '미제공')
        self.assertContains(response, '종목당 신청인원')
        self.assertNotContains(response, '수혜율')
        self.assertNotContains(response, 'NaN')
