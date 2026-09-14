"""Program module regressions. CSV access is mocked at the repository boundary."""
import csv
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse

from . import models, views
from .services import filter_programs, program_facility_types


def program(**overrides):
    row = dict(id='program-0', facility='시설', region='서울', district='중구', address='주소',
               phone='02-000', facility_type='수영장', name='A', sport='수영', target='성인',
               weekday='월수금', time='19:00~19:50', period='2025-03-01 ~ 2025-03-31',
               capacity=20, fee=50000, fee_unit='단위 미확인', homepage='', walk_minutes=3, stop='정류장')
    row.update(overrides)
    return models.Program(**row)


REPORT = {'register_rows': 5, 'programs': 3, 'duplicates': 2,
          'facilities': 2, 'source': 'x.csv'}


class ProgramServiceTests(SimpleTestCase):
    def setUp(self):
        self.rows = [program(id='b', name='B', region='서울', fee=2000, walk_minutes=9,
                             capacity=5, target='청소년', weekday='화목', facility_type='체육관'),
                     program(id='a', name='A', region='부산', fee=1000, walk_minutes=1,
                             capacity=50, target='성인', weekday='월수금', facility_type='수영장')]

    def test_sort_does_not_mutate_cached_repository_rows(self):
        with patch('app.programs.services.models.programs', return_value=self.rows):
            result = filter_programs({'sort': 'fee'})
        self.assertEqual([row.id for row in result], ['a', 'b'])
        self.assertEqual([row.id for row in self.rows], ['b', 'a'])
        self.assertIsNot(result, self.rows)

    def test_walk_and_capacity_sorts_keep_missing_values_last(self):
        rows = [*self.rows, program(id='c', name='C', walk_minutes=None, capacity=None)]
        with patch('app.programs.services.models.programs', return_value=rows):
            self.assertEqual([r.id for r in filter_programs({'sort': 'walk'})], ['a', 'b', 'c'])
            self.assertEqual([r.id for r in filter_programs({'sort': 'capacity'})], ['a', 'b', 'c'])

    def test_target_weekday_and_facility_type_filters(self):
        with patch('app.programs.services.models.programs', return_value=self.rows):
            self.assertEqual([r.id for r in filter_programs({'target': '청소년'})], ['b'])
            self.assertEqual([r.id for r in filter_programs({'weekday': '금'})], ['a'])
            self.assertEqual([r.id for r in filter_programs({'facility_type': '체육관'})], ['b'])
        self.assertEqual(program_facility_types(self.rows), ['수영장', '체육관'])


class ProgramRepositoryTests(SimpleTestCase):
    BASE = ('1100000000', '서울특별시', '1120000000', '성동구', '테스트센터',
            '서울특별시 성동구 무수막길 69', '0222047900', '수영장', '수영', '저녁수영',
            '성인,<br>청소년(13세이상)', '20260701', '20260731', '월화수목금', '19:00-19:50',
            '25', '49500.00000', '', 'https://example.test', '금호역', '600', '120', '', '', '')

    def _load(self, rows):
        models._snapshot.cache_clear()
        self.addCleanup(models._snapshot.cache_clear)
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory) / models.PROGRAM_FILE).open('w', encoding='utf-8-sig', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(models.COLUMNS)
                writer.writerows(rows)
            with override_settings(DATA_DIR=directory):
                return models.programs(), models.load_report()

    def test_identical_rows_collapse_and_are_counted(self):
        different = list(self.BASE)
        different[models.TIZN] = '20:00-20:50'
        rows, report = self._load([self.BASE, self.BASE, different])
        self.assertEqual(len(rows), 2)
        self.assertEqual(report['duplicates'], 1)
        self.assertEqual(report['register_rows'], 3)
        self.assertEqual(report['facilities'], 1)

    def test_source_fields_are_normalised_without_inventing_values(self):
        rows, _ = self._load([self.BASE])
        row = rows[0]
        self.assertEqual(row.target, '성인, 청소년(13세이상)')
        self.assertEqual(row.period, '2026-07-01 ~ 2026-07-31')
        self.assertEqual(row.fee, 49500)
        self.assertEqual(row.fee_unit, '단위 미확인')
        self.assertEqual(row.capacity, 25)
        self.assertEqual(row.walk_minutes, 2)

    def test_blank_programme_type_falls_back_to_the_facility_industry(self):
        blank = list(self.BASE)
        blank[models.PROGRM_TY_NM] = ''
        rows, _ = self._load([blank])
        self.assertEqual(rows[0].sport, '수영장')

    def test_missing_walk_times_stay_missing(self):
        nowalk = list(self.BASE)
        for index in models.WALK:
            nowalk[index] = ''
        rows, _ = self._load([nowalk])
        self.assertIsNone(rows[0].walk_minutes)


class ProgramViewTests(SimpleTestCase):
    def setUp(self):
        self.rows = [program(id='b', name='B', region='서울'), program(id='a', name='A', region='부산')]

    def test_page_and_export_use_same_filters(self):
        with patch('app.programs.models.programs', return_value=self.rows), \
             patch('app.programs.models.load_report', return_value=REPORT):
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
        self.assertEqual(records[1][0], response.context['top_results'][0].id)
        self.assertIn('정류장 도보(분)', records[0])

    def test_page_states_its_own_source_and_deduplication(self):
        with patch('app.programs.models.programs', return_value=self.rows), \
             patch('app.programs.models.load_report', return_value=REPORT):
            response = self.client.get(reverse('programs'))
        self.assertContains(response, '공공체육시설 프로그램 정보')
        self.assertContains(response, '중복 2행을 제외해 3건을 적재했습니다')

    def test_oversized_export_is_refused_instead_of_truncated(self):
        rows = [program(id=str(i)) for i in range(3)]
        with patch('app.programs.models.programs', return_value=rows),              patch('app.programs.models.load_report', return_value=REPORT),              patch('app.common.exports.EXPORT_ROW_LIMIT', 2),              patch('app.programs.views.EXPORT_ROW_LIMIT', 2):
            page = self.client.get(reverse('programs'))
            refused = self.client.get(reverse('export_programs'))
            allowed = self.client.get(reverse('export_programs'), {'region': '부산'})
        self.assertEqual(refused.status_code, 400)
        self.assertIn('검색 조건을 좁혀', refused.content.decode())
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(page, '조건을 좁혀야 내보낼 수 있습니다')
        self.assertNotContains(page, '엑셀 내보내기')

    def test_url_resolves_to_module_controller(self):
        self.assertIs(resolve('/programs').func, views.programs)
        self.assertIs(resolve('/export/programs.xlsx').func, views.export_programs)
