"""Facility controller and filtered export regressions."""
from openpyxl import load_workbook
from io import BytesIO
from unittest.mock import patch
from django.test import SimpleTestCase
from django.urls import resolve

from . import views


class FacilityModuleTests(SimpleTestCase):
    def test_module_routes_and_export_escaping(self):
        rows = [dict(id='1', name='=1+1', region='서울', address='주소', phone='010-1234',
                     sport='수영', voucher='등록')]
        self.assertIs(resolve('/facilities').func, views.facilities)
        self.assertIs(resolve('/export/facilities.xlsx').func, views.export_facilities)
        with patch('app.facilities.views.facility_rows', return_value=rows):
            page = self.client.get('/facilities', {'region': '서울', 'facilityId': '1'})
            export = self.client.get('/export/facilities.xlsx', {'region': '서울'})
            empty = self.client.get('/export/facilities.xlsx', {'region': '부산'})
        self.assertTemplateUsed(page, 'facilities/index.html')
        self.assertEqual(page.context['selected']['name'], '=1+1')
        workbook = load_workbook(BytesIO(export.content))
        records = list(workbook.active.values)
        self.assertEqual(records[1][1], '=1+1')
        self.assertEqual(workbook.active['B2'].data_type, 's')
        self.assertEqual(workbook.active['E2'].value, '010-1234')
        self.assertEqual(workbook.active.freeze_panes, 'A2')
        self.assertEqual(workbook.active.auto_filter.ref, 'A1:G2')
        self.assertIn('SPORT_INSIGHT_facilities.xlsx', export['Content-Disposition'])
        self.assertContains(page, '엑셀 내보내기')
        self.assertEqual(len(list(load_workbook(BytesIO(empty.content)).active.values)), 1)
