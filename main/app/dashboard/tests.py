"""Dashboard controller and repository boundary tests."""
import csv
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import resolve

from . import models, views
from .services import courses_per_facility, dashboard_data, requests_per_course


def area(**overrides):
    row = dict(region='서울', district='중구', facilities=2, courses=5, requests=100,
               sports=Counter({'수영': 100}), first_month='2025-01', last_month='2025-06')
    row.update(overrides)
    return row


class DashboardServiceTests(SimpleTestCase):
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
            self.assertEqual(dashboard_data()['sports'], [('수영', 150), ('축구', 0)])
            self.assertEqual(dashboard_data('부산')['sports'], [('수영', 50)])

    def test_ratios_require_a_known_positive_denominator(self):
        self.assertEqual(courses_per_facility(2, 5), 2.5)
        self.assertIsNone(courses_per_facility(0, 5))
        self.assertIsNone(requests_per_course(5, None))


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


class DashboardViewTests(SimpleTestCase):
    def test_module_route_and_template(self):
        self.assertIs(resolve('/dashboard').func, views.dashboard)
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard')
        self.assertTemplateUsed(response, 'dashboard/index.html')

    def test_page_reports_usage_counts_and_states_the_missing_coverage_source(self):
        snapshot = {'areas': [area(requests=0), area(district='종로구', requests=None)],
                    'months': ['2025-01'], 'ledger_rows': 4, 'unidentified': 0, 'source': 'x.csv'}
        with patch('app.dashboard.models.usage_snapshot', return_value=snapshot):
            response = self.client.get('/dashboard')
        self.assertEqual(response.context['region_chart_max'], 0)
        self.assertContains(response, '<span>0</span>', html=True)
        self.assertContains(response, '<span>미제공</span>', html=True)
        self.assertContains(response, '지원대상·수급인원 자료가')
        self.assertNotContains(response, 'NaN')
