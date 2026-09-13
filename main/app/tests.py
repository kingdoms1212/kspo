from django.test import SimpleTestCase
from html.parser import HTMLParser
from unittest.mock import patch

from .services import benefit_rate, calculate_budget, nearest_stop_minutes


class ShellParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.navigation = []
        self.current = []
        self.skip_target = None
        self.main_target = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'nav-link' in attrs.get('class', '').split():
            self.navigation.append(attrs.get('href'))
            if attrs.get('aria-current') == 'page':
                self.current.append(attrs.get('href'))
        if tag == 'a' and attrs.get('class') == 'skip-link':
            self.skip_target = attrs.get('href')
        if tag == 'main' and attrs.get('tabindex') == '-1':
            self.main_target = '#' + attrs.get('id', '')


class ShellTests(SimpleTestCase):
    def test_root_redirects_without_loading_data(self):
        with patch('app.views.dashboard_data') as loader:
            response = self.client.get('/')
        self.assertRedirects(response, '/dashboard', fetch_redirect_response=False)
        loader.assert_not_called()

    def test_three_pages_navigation_source_status_and_focus_target(self):
        with patch('app.views.dashboard_data', return_value={}), \
             patch('app.views.filter_programs', return_value=[]), \
             patch('app.views.facility_rows', return_value=[]):
            for route in ('/dashboard', '/programs', '/facilities'):
                with self.subTest(route=route):
                    response = self.client.get(route)
                    self.assertEqual(response.status_code, 200)
                    parser = ShellParser()
                    parser.feed(response.content.decode())
                    self.assertEqual(parser.navigation, ['/dashboard', '/programs', '/facilities'])
                    self.assertEqual(parser.current, [route])
                    self.assertEqual(parser.skip_target, '#main-content')
                    self.assertEqual(parser.main_target, parser.skip_target)
                    self.assertContains(response, '실제 자료 모드 · 검증 진행 중')
                    self.assertContains(response, '지도: 행정경계 데이터 미연결')
                    self.assertContains(response, 'sport-insight-colors.css')
                    self.assertNotContains(response, 'fonts.googleapis.com')
                    self.assertNotContains(response, '⚙ 설정')

    def test_program_table_can_receive_keyboard_focus(self):
        with patch('app.views.filter_programs', return_value=[]):
            response = self.client.get('/programs')
        self.assertContains(response, 'tabindex="0" role="region" aria-label="프로그램 비교표 가로 스크롤"')


class DesignInteractionTests(SimpleTestCase):
    def test_program_pagination_keeps_top_three_and_export_filters(self):
        rows = [dict(id=str(i), name=f'테스트 강좌 {i:02}', facility='테스트 시설',
                     region='서울', sport='수영', target='청소년', weekday='월',
                     fee='1000', fee_unit='미확인', period='기간 미제공') for i in range(23)]
        with patch('app.views.filter_programs', return_value=rows):
            response = self.client.get('/programs', {'region': '서울', 'sport': '수영',
                                                     'target': '청소년', 'sort': 'name', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['page_obj']), rows[20:])
        self.assertEqual(response.context['top_results'], rows[:3])
        from urllib.parse import parse_qs
        filters = parse_qs(response.context['export_query'])
        self.assertEqual(filters['sport'], ['수영'])
        self.assertEqual(filters['region'], ['서울'])
        self.assertEqual(filters['target'], ['청소년'])
        self.assertNotIn('page', filters)
        self.assertContains(response, '21–23 / 23건')

    def test_facility_page_and_selection_preserve_filter_and_escape_text(self):
        rows = [dict(id=f'facility-{i}', name=f'테스트 시설 {i}', region='서울', district='중구',
                     address='<script>test</script>', phone='', sport='수영', voucher='스포츠 등록') for i in range(23)]
        with patch('app.views.facility_rows', return_value=rows):
            response = self.client.get('/facilities', {'region': '서울', 'query': '테스트',
                                                       'facilityId': 'facility-22', 'page': 2})
        self.assertEqual(response.context['selected']['id'], 'facility-22')
        self.assertEqual(list(response.context['page_obj']), rows[20:])
        self.assertContains(response, 'selected-row')
        self.assertContains(response, '&lt;script&gt;test&lt;/script&gt;')
        self.assertNotContains(response, '<script>test</script>')
        self.assertContains(response, '시설 사진 미제공')

    def test_regional_chart_preserves_zero_missing_and_source_definition(self):
        rows = [dict(region='서울', district='중구', beneficiary=0, definition='테스트 대상', period='2024'),
                dict(region='서울', district='종로구', beneficiary=None, definition='테스트 대상', period='2024')]
        with patch('app.views.dashboard_data', return_value={'regions': rows, 'period': ['2024']}):
            response = self.client.get('/dashboard')
        self.assertEqual(response.context['region_chart_max'], 0)
        self.assertContains(response, '테스트 대상 · 2024')
        self.assertContains(response, '<span>0</span>', html=True)
        self.assertContains(response, '<span>미제공</span>', html=True)
        self.assertNotContains(response, 'NaN')


class CalculationTests(SimpleTestCase):
	def test_budget_within_limit(self):
		result = calculate_budget(30_000_000, 100, 6, 50_000)
		self.assertEqual(result['cost'], 30_000_000)
		self.assertEqual(result['supported_people'], 100)
		self.assertEqual(result['status'], 'within_budget')

	def test_budget_over_limit(self):
		result = calculate_budget(29_999_999, 100, 6, 50_000)
		self.assertEqual(result['supported_people'], 99)
		self.assertEqual(result['status'], 'over_budget')

	def test_unverified_plan_is_not_calculated(self):
		self.assertEqual(calculate_budget(1_000_000, None, 6, 50_000)['status'], 'invalid_plan')
		self.assertEqual(calculate_budget(1_000_000, 1, 6, None)['status'], 'unverified_fee')

	def test_zero_fee_does_not_create_infinite_people(self):
		result = calculate_budget(1_000_000, 10, 6, 0)
		self.assertIsNone(result['supported_people'])
		self.assertEqual(result['cost'], 0)

	def test_rate_requires_known_positive_denominator(self):
		self.assertEqual(benefit_rate(100, 14), 0.14)
		self.assertIsNone(benefit_rate(0, 14))
		self.assertIsNone(benefit_rate(None, 14))

	def test_nearest_stop_ignores_missing_values(self):
		self.assertEqual(nearest_stop_minutes([None, 180, 240]), 3)
		self.assertIsNone(nearest_stop_minutes([None, -1]))
