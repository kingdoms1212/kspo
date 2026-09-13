"""Program module regressions. CSV access is mocked at the repository boundary."""
from openpyxl import load_workbook
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from . import views
from .services import filter_programs


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

    def test_url_resolves_to_module_controller(self):
        self.assertIs(resolve('/programs').func, views.programs)
        self.assertIs(resolve('/export/programs.xlsx').func, views.export_programs)
