"""Dashboard controller and repository boundary tests."""
from unittest.mock import patch
from django.test import SimpleTestCase
from django.urls import resolve

from . import views
from .services import dashboard_data


class DashboardModuleTests(SimpleTestCase):
    def test_module_route_and_template(self):
        self.assertIs(resolve('/dashboard').func, views.dashboard)
        with patch('app.dashboard.views.dashboard_data', return_value={}):
            response = self.client.get('/dashboard')
        self.assertTemplateUsed(response, 'dashboard/index.html')

    def test_region_filter_and_zero_are_preserved(self):
        rows = [dict(region='서울', target=100, beneficiary=0, facility_count=2, period='2024'),
                dict(region='부산', target=200, beneficiary=50, facility_count=3, period='2024')]
        from collections import Counter
        with patch('app.dashboard.models.coverage', return_value=rows), \
             patch('app.dashboard.models.usage_by_sport', return_value=Counter()), \
             patch('app.dashboard.services.programs', return_value=[]):
            result = dashboard_data('서울')
        self.assertEqual(result['target'], 100)
        self.assertEqual(result['beneficiary'], 0)
        self.assertEqual(len(result['regions']), 1)
