"""Program module regressions. CSV access is mocked at the repository boundary."""
from openpyxl import load_workbook
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from . import models, views
from .services import (
    filter_programs,
    program_budget_plan,
    program_districts,
    program_region_district_map,
    program_seoul_district_distribution,
)


class ProgramModuleTests(SimpleTestCase):
    def setUp(self):
        self.rows = [
            dict(id='b', name='B', facility='시설', region='서울', district='중구',
                 sport='수영', target='청소년', weekday='월', period='', fee='2000', fee_unit='원'),
            dict(id='a', name='A', facility='시설', region='부산', district='중구',
                 sport='축구', target='성인', weekday='화', period='', fee='1000', fee_unit='원'),
        ]

    def test_sort_does_not_mutate_cached_repository_rows(self):
        with patch('app.programs.services.models.programs', return_value=self.rows):
            result = filter_programs({'sort': 'fee'})
        self.assertEqual([row['id'] for row in result], ['a', 'b'])
        self.assertEqual([row['id'] for row in self.rows], ['b', 'a'])
        self.assertIsNot(result, self.rows)

    def test_district_options_are_grouped_deduplicated_and_sorted(self):
        rows = [
            dict(region='서울특별시', district='금천구'),
            dict(region='서울특별시', district='관악구'),
            dict(region='서울특별시', district='금천구'),
            dict(region='경기도', district='수원시'),
            dict(region='지역 미제공', district='미확인'),
            dict(region='서울특별시', district=''),
        ]

        mapping = program_region_district_map(rows)

        self.assertEqual(mapping['서울특별시'], ['관악구', '금천구'])
        self.assertEqual(mapping['경기도'], ['수원시'])
        self.assertNotIn('지역 미제공', mapping)
        self.assertEqual(program_districts(rows, '서울특별시'), ['관악구', '금천구'])
        self.assertEqual(program_districts(rows, ''), [])

    def test_program_repository_uses_public_facility_program_source(self):
        source_row = {
            'FCLTY_NM': '공공체육센터',
            'CTPRVN_NM': '서울특별시',
            'SIGNGU_NM': '강남구',
            'PROGRM_NM': '생활 수영',
            'PROGRM_TY_NM': '수영',
            'PROGRM_TRGET_NM': '성인',
            'PROGRM_ESTBL_WKDAY_NM': '월수금',
            'PROGRM_BEGIN_DE': '20260101',
            'PROGRM_END_DE': '20260131',
            'PROGRM_PRC': '50000.00000',
        }
        models.programs.cache_clear()
        try:
            with patch('app.programs.models._read_rows', return_value=[source_row]) as read_rows:
                result = models.programs()
        finally:
            models.programs.cache_clear()

        read_rows.assert_called_once_with('공공체육시설 프로그램 정보.csv', limit=15000)
        self.assertEqual(result[0]['facility'], '공공체육센터')
        self.assertEqual(result[0]['name'], '생활 수영')
        self.assertEqual(result[0]['sport'], '수영')
        self.assertEqual(result[0]['source'], '공공체육시설 프로그램 정보.csv')

    def test_seoul_district_distribution_counts_filtered_rows(self):
        rows = [
            dict(region='서울특별시', district='관악구'),
            dict(region='서울', district='관악구'),
            dict(region='서울특별시', district='금천구'),
            dict(region='경기도', district='관악구'),
            dict(region='서울특별시', district=''),
        ]

        distribution = dict(program_seoul_district_distribution(rows))

        self.assertEqual(distribution, {'관악구': 2, '금천구': 1})

    def test_budget_plan_converts_thousand_won_and_filters_program_fee(self):
        params = {
            'budget_min': '100',
            'budget_max': '200',
        }
        rows = [
            {**self.rows[0], 'fee': '100000'},
            {**self.rows[1], 'fee': '300000'},
        ]

        plan = program_budget_plan(params)
        with patch('app.programs.services.models.programs', return_value=rows):
            result = filter_programs(params, budget_plan=plan)

        self.assertTrue(plan['valid'])
        self.assertEqual(plan['minimum_won'], 100_000)
        self.assertEqual(plan['maximum_won'], 200_000)
        self.assertEqual([item['id'] for item in result], ['b'])

    def test_invalid_budget_plan_does_not_hide_search_results(self):
        params = {
            'budget_min': '200',
            'budget_max': '100',
        }

        plan = program_budget_plan(params)
        with patch('app.programs.services.models.programs', return_value=self.rows):
            result = filter_programs(params, budget_plan=plan)

        self.assertFalse(plan['valid'])
        self.assertIn('최소 예산', plan['error'])
        self.assertEqual(len(result), 2)

    def test_page_and_export_use_same_filters(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'), {'region': '서울'})
            export = self.client.get(reverse('export_programs'), {'region': '서울'})
        self.assertTemplateUsed(response, 'programs/index.html')
        self.assertEqual(response.context['result_count'], 1)
        workbook = load_workbook(BytesIO(export.content))
        records = list(workbook.active.values)
        self.assertEqual(export['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('SPORT_INSIGHT_programs.xlsx', export['Content-Disposition'])
        self.assertContains(response, '엑셀 내보내기')
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1][0], response.context['top_results'][0]['id'])

    def test_program_page_exposes_dependent_district_options(self):
        rows = [
            dict(id='1', name='수영', facility='시설', region='서울특별시', district='관악구',
                 sport='수영', target='청소년', weekday='월', period='', fee='1000', fee_unit='원'),
            dict(id='2', name='축구', facility='시설', region='서울특별시', district='금천구',
                 sport='축구', target='청소년', weekday='화', period='', fee='2000', fee_unit='원'),
            dict(id='3', name='농구', facility='시설', region='경기도', district='수원시',
                 sport='농구', target='청소년', weekday='수', period='', fee='3000', fee_unit='원'),
        ]
        with patch('app.programs.models.programs', return_value=rows):
            response = self.client.get(reverse('programs'), {
                'region': '서울특별시',
                'district': '관악구',
            })

        self.assertEqual(response.context['districts'], ['관악구', '금천구'])
        self.assertEqual(response.context['params']['district'], '관악구')
        self.assertEqual(response.context['region_district_map']['경기도'], ['수원시'])
        self.assertContains(response, 'id="district"')
        self.assertContains(response, 'id="region-district-map"')

    def test_program_page_preserves_budget_range_without_removed_fields(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'), {
                'budget_min': '1000',
                'budget_max': '2000',
            })

        self.assertTrue(response.context['budget_plan']['active'])
        self.assertContains(response, 'name="budget_min"')
        self.assertContains(response, 'value="1000"')
        self.assertNotContains(response, 'name="planned_people"')
        self.assertNotContains(response, 'name="support_months"')
        self.assertNotContains(response, 'name="target"')
        self.assertNotContains(response, 'class="budget-filter"')
        self.assertNotContains(response, '조건을 입력한 후 조회를 눌러 적용하세요')
        self.assertNotContains(response, '수강료 단위는 별도 확인이 필요합니다')

    def test_program_page_exposes_echarts_region_map(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'))

        self.assertContains(response, '추천 시설 및 지역 분포')
        self.assertContains(response, 'id="program-region-map"')
        self.assertContains(response, 'id="program-region-distribution"')
        self.assertContains(response, 'id="program-seoul-district-distribution"')
        self.assertContains(response, 'id="program-map-back"')
        self.assertContains(response, 'echarts@5.6.0')
        self.assertContains(response, 'seoul_municipalities_geo_simple.json')
        self.assertContains(response, 'id="program-scroll-position"')
        self.assertContains(response, 'activeRegions.length === 1')
        self.assertContains(response, "backgroundColor: '#e6edf5'")
        self.assertContains(response, "areaColor: '#f7fbff'")

    def test_program_heading_description_uses_accessible_tooltip(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'))

        self.assertContains(response, 'class="heading-help"')
        self.assertContains(response, 'aria-describedby="program-heading-tooltip"')
        self.assertContains(response, 'id="program-heading-tooltip" class="heading-tooltip" role="tooltip"')
        self.assertContains(response, '지역과 종목별로 등록 강좌를 조회하고 비교합니다.')
        self.assertContains(response, 'href="#i-alert"')

    def test_top_program_cards_show_compact_fee_and_weekday_tags(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'))

        top_cards = response.content.decode().split('class="program-cards"', 1)[1].split('</section>', 1)[0]
        self.assertIn('수강료 <b>1,000원</b>', top_cards)
        self.assertIn('강좌 요일 <b>화</b>', top_cards)
        self.assertLess(top_cards.index('축구'), top_cards.index('강좌 요일 <b>화</b>'))
        self.assertLess(top_cards.index('강좌 요일 <b>화</b>'), top_cards.index('수강료 <b>1,000원</b>'))
        self.assertNotIn('가격 단위', top_cards)
        self.assertNotIn('program-period', top_cards)
        self.assertNotIn('청소년', top_cards)

    def test_comparison_table_hides_target_and_formats_fee(self):
        with patch('app.programs.models.programs', return_value=self.rows):
            response = self.client.get(reverse('programs'))

        comparison_table = response.content.decode().split('aria-label="프로그램 비교표 가로 스크롤"', 1)[1].split('</table>', 1)[0]
        self.assertIn('<th scope="col">종목</th>', comparison_table)
        self.assertIn('<th scope="col">수강료</th>', comparison_table)
        self.assertIn('<td class="price">1,000원</td>', comparison_table)
        self.assertIn('<td class="price">2,000원</td>', comparison_table)
        self.assertNotIn('종목 / 대상', comparison_table)
        self.assertNotIn('수강료 / 단위', comparison_table)
        self.assertNotIn('청소년', comparison_table)
        self.assertNotIn('성인', comparison_table)
        self.assertNotIn('단위 미확인', comparison_table)

    def test_url_resolves_to_module_controller(self):
        self.assertIs(resolve('/programs').func, views.programs)
        self.assertIs(resolve('/export/programs.xlsx').func, views.export_programs)
