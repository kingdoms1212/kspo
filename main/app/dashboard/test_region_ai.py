from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings

@override_settings(AI_REVIEW_MODE='gemini')
class RegionAITests(SimpleTestCase):
    def test_cached_summary_and_generation_change(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': ['강서구']}}
        result = {'summary': '현황 요약', 'features': ['특징'], 'considerations': ['확인 사항']}
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('app.dashboard.ai_views.source_version', return_value=('manifest', 'one')) as generation, patch('app.dashboard.ai_views.dashboard_data', return_value=stats), patch('app.dashboard.ai_views.GeminiClient.review', return_value=result) as ai:
            first = self.client.post('/dashboard/ai/region', {'district': '강서구'}).json()
            second = self.client.post('/dashboard/ai/region', {'district': '강서구'}).json()
            self.assertFalse(first['cached'])
            self.assertTrue(second['cached'])
            self.assertEqual(ai.call_count, 1)
            generation.return_value = ('manifest', 'two')
            self.client.post('/dashboard/ai/region', {'district': '강서구'})
            self.assertEqual(ai.call_count, 2)
            self.assertEqual(self.client.post('/dashboard/ai/region', {'district': '없는구'}).status_code, 400)

    def test_failures_are_not_cached_and_bad_output_is_rejected(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('app.dashboard.ai_views.source_version', return_value=('manifest', 'one')), patch('app.dashboard.ai_views.dashboard_data', return_value=stats), patch('app.dashboard.ai_views.GeminiClient.review', return_value={'summary': 'incomplete'}) as ai:
            for _ in range(2): self.assertEqual(self.client.post('/dashboard/ai/region').status_code, 503)
            self.assertEqual(ai.call_count, 2)

    def test_cache_write_failure_keeps_successful_analysis(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        result = {'summary': '요약', 'features': [], 'considerations': []}
        with patch('app.dashboard.ai_views.source_version', return_value=('manifest', 'one')), patch('app.dashboard.ai_views.dashboard_data', return_value=stats), patch('app.dashboard.ai_views.FileBasedCache') as cache, patch('app.dashboard.ai_views.GeminiClient.review', return_value=result):
            cache.return_value.get.return_value = None
            cache.return_value.set.side_effect = OSError('disk unavailable')
            response = self.client.post('/dashboard/ai/region')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], result)

    def test_blank_summary_is_rejected(self):
        from .ai_views import validate_region_result
        with self.assertRaises(ValueError):
            validate_region_result({'summary': '   ', 'features': [], 'considerations': []})

    def test_corrupt_cache_is_replaced(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        result = {'summary': '새 요약', 'features': [], 'considerations': []}
        with patch('app.dashboard.ai_views.source_version', return_value=('manifest', 'one')), patch('app.dashboard.ai_views.dashboard_data', return_value=stats), patch('app.dashboard.ai_views.FileBasedCache') as cache, patch('app.dashboard.ai_views.GeminiClient.review', return_value=result) as ai:
            cache.return_value.get.return_value = {'result': {'summary': 'incomplete'}}
            response = self.client.post('/dashboard/ai/region')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['cached'])
        ai.assert_called_once()
