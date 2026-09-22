from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from app.ai_review.contracts import AIResponse
from django.test import SimpleTestCase, override_settings

@override_settings(AI_MODE='live', AI_PROVIDER='gemini', AI_MODEL='gemini-test')
class RegionAITests(SimpleTestCase):
    def test_cached_summary_and_generation_change(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': ['강서구']}}
        result = {'summary': '현황 요약', 'features': ['특징'], 'considerations': ['확인 사항']}
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('app.ai_review.region_service.source_version', return_value=('manifest', 'one')) as generation, patch('app.ai_review.region_service.dashboard_data', return_value=stats), patch('app.ai_review.region_service.create_provider') as ai:
            ai.return_value.generate.return_value = AIResponse(result, 'gemini', 'gemini-test')
            first = self.client.post('/dashboard/ai/region', {'district': '강서구'}).json()
            second = self.client.post('/dashboard/ai/region', {'district': '강서구'}).json()
            self.assertFalse(first['cached'])
            self.assertTrue(second['cached'])
            self.assertEqual(ai.call_count, 1)
            generation.return_value = ('manifest', 'two')
            self.client.post('/dashboard/ai/region', {'district': '강서구'})
            self.assertEqual(ai.call_count, 2)
            with override_settings(AI_PROVIDER='another-provider'):
                self.client.post('/dashboard/ai/region', {'district': '강서구'})
            self.assertEqual(ai.call_count, 3)
            self.assertEqual(self.client.post('/dashboard/ai/region', {'district': '없는구'}).status_code, 400)

    def test_failures_are_not_cached_and_bad_output_is_rejected(self):
        result = {'summary': 'incomplete'}
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('app.ai_review.region_service.source_version', return_value=('manifest', 'one')), patch('app.ai_review.region_service.dashboard_data', return_value=stats), patch('app.ai_review.region_service.create_provider') as ai:
            ai.return_value.generate.return_value = AIResponse(result, 'gemini', 'gemini-test')
            for _ in range(2): self.assertEqual(self.client.post('/dashboard/ai/region').status_code, 503)
            self.assertEqual(ai.call_count, 2)

    def test_cache_write_failure_keeps_successful_analysis(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        result = {'summary': '요약', 'features': [], 'considerations': []}
        with patch('app.ai_review.region_service.source_version', return_value=('manifest', 'one')), patch('app.ai_review.region_service.dashboard_data', return_value=stats), patch('app.ai_review.region_service.FileBasedCache') as cache, patch('app.ai_review.region_service.create_provider') as ai:
            ai.return_value.generate.return_value = AIResponse(result, 'gemini', 'gemini-test')
            cache.return_value.get.return_value = None
            cache.return_value.set.side_effect = OSError('disk unavailable')
            response = self.client.post('/dashboard/ai/region')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], result)

    def test_blank_summary_is_rejected(self):
        from app.ai_review.region_service import validate_region_result
        with self.assertRaises(ValueError):
            validate_region_result({'summary': '   ', 'features': [], 'considerations': []})

    def test_corrupt_cache_is_replaced(self):
        stats = {'facilities': 1, 'courses': 2, 'requests': 3, 'sport_rows': [], 'period': [], 'region_district_options': {'서울': []}}
        result = {'summary': '새 요약', 'features': [], 'considerations': []}
        with patch('app.ai_review.region_service.source_version', return_value=('manifest', 'one')), patch('app.ai_review.region_service.dashboard_data', return_value=stats), patch('app.ai_review.region_service.FileBasedCache') as cache, patch('app.ai_review.region_service.create_provider') as ai:
            ai.return_value.generate.return_value = AIResponse(result, 'gemini', 'gemini-test')
            cache.return_value.get.return_value = {'result': {'summary': 'incomplete'}}
            response = self.client.post('/dashboard/ai/region')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['cached'])
        ai.assert_called_once()

    def test_key_presence_is_logged_without_key_value(self):
        for value, expected in [('', 'False'), ('private-api-key', 'True')]:
            with patch.dict('os.environ', {'GEMINI_API_KEY': value, 'RENDER': 'true'}), patch('app.ai_review.region_service.source_version', side_effect=OSError('data unavailable')), self.assertLogs('app.ai_review.region_service', level='INFO') as logs:
                self.client.post('/dashboard/ai/region')
            output = '\n'.join(logs.output)
            self.assertIn('key_configured=' + expected, output)
            self.assertIn('on_render=True', output)
            self.assertNotIn('private-api-key', output)
