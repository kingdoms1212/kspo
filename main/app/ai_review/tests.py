import json
import os
from unittest.mock import MagicMock, patch
import httpx
from google.genai import errors, types

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from .client import GeminiClient, ReviewError
from .schemas import CRITERIA, normalize_analysis
from .services import build_evidence, review_plan


def example_response(keys=('sports_demand',)):
    return {'summary': '자료가 부족하므로 추가 확인이 필요합니다.',
            'evaluations': {key: {'score': None, 'reason': '확인 자료가 없습니다.', 'evidence_keys': []} for key in keys},
            'strengths': [], 'risks': ['자료 부족'], 'recommendations': ['자료 보완'], 'limitations': ['일부 평가 불가']}


@override_settings(AI_REVIEW_MODE='gemini', GEMINI_MODEL='gemini-3.1-flash-lite', GEMINI_TIMEOUT_SECONDS=2,
                   AI_REVIEW_INCLUDE_TRANSIT=False)
class AnalysisTests(SimpleTestCase):
    def setUp(self):
        self.plan = {'region': '서울', 'district': '강서구', 'sport': '수영', 'fee': 10000}
        self.stats = {'sports': [('수영', 120)], 'requests': 200, 'sport_rows': []}
        self.evidence = build_evidence(self.plan, [], self.stats)

    def test_mapping_does_not_invent_population_budget_or_transport(self):
        for key in ('population', 'welfare', 'program_budget', 'transport', 'participation_rate'):
            self.assertNotIn(key, self.evidence)
        self.assertEqual(self.evidence['plan']['fee'], 10000)
        self.assertEqual(self.evidence['sport_requests'], 120)
        self.assertNotIn('budget_feasibility', self.evidence['available_criteria'])

    def test_missing_scores_are_not_zero_and_mean_is_server_computed(self):
        data = example_response()
        self.assertIsNone(normalize_analysis(data, self.evidence)['overall_score'])
        data['evaluations']['sports_demand'] = {'score': 80, 'reason': '이용현황 기준 의견', 'evidence_keys': ['sport_requests']}
        result = normalize_analysis(data, self.evidence)
        self.assertEqual(result['overall_score'], 80)
        self.assertEqual(result['scored_count'], 1)
        self.assertEqual(result['grade'], '매우 적합')
        self.assertEqual(result['criterion_count'], 1)
        self.assertEqual(len(result['findings']), 1)

    def test_rejects_unsupported_and_invalid_scores(self):
        for score in (True, 101, -1, 2.5, '80', 80):
            data = example_response()
            data['evaluations']['sports_demand']['score'] = score
            with self.assertRaises(ValueError):
                normalize_analysis(data, self.evidence)

    def test_missing_key_does_not_call_network(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}), patch('app.ai_review.client.genai.Client') as call:
            result = review_plan(self.plan, [], self.stats, timezone.now())
        call.assert_not_called()
        self.assertEqual(result['error_code'], 'missing_key')

    def test_official_request_separates_instruction_and_json(self):
        response = types.GenerateContentResponse(candidates=[types.Candidate(
            finish_reason='STOP', content=types.Content(parts=[types.Part(text=json.dumps(example_response()))]))])
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-secret'}), patch('app.ai_review.client.genai.Client') as factory:
            call = factory.return_value.__enter__.return_value.models.generate_content
            call.return_value = response
            result = review_plan(self.plan, [], self.stats, timezone.now())
        config = call.call_args.kwargs['config']
        self.assertEqual(config.response_mime_type, 'application/json')
        self.assertEqual(config.response_json_schema['properties']['evaluations']['required'], ['sports_demand'])
        self.assertTrue(config.system_instruction)
        self.assertTrue(config.automatic_function_calling.disable)
        self.assertEqual(json.loads(call.call_args.kwargs['contents'])['plan']['sport'], '수영')
        self.assertEqual(factory.call_args.kwargs['http_options'].timeout, 2000)
        self.assertEqual(factory.call_args.kwargs['http_options'].retry_options.attempts, 11)
        self.assertEqual(factory.call_args.kwargs['http_options'].retry_options.http_status_codes, [429, 500, 502, 503, 504])
        self.assertEqual(result['status'], 'completed')
        factory.return_value.__exit__.assert_called_once()

    def test_errors_preserve_report_and_do_not_log_secret(self):
        failures = [(httpx.ReadTimeout('test-secret'), 'timeout'), (httpx.ConnectError('test-secret'), 'network'),
                    (errors.ClientError(429, {'error': {'message': 'test-secret'}}), 'rate_limit'),
                    (errors.ServerError(503, {'error': {'message': 'test-secret'}}), 'http_503'),
                    (errors.ClientError(400, {'error': {'message': 'test-secret'}}), 'http_400')]
        for error, code in failures:
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-secret'}), \
                    patch('app.ai_review.client.genai.Client') as factory, \
                    self.assertLogs('app.ai_review.services', level='WARNING') as logs:
                factory.return_value.__enter__.return_value.models.generate_content.side_effect = error
                result = review_plan(self.plan, [], self.stats, timezone.now())
            self.assertEqual(result['error_code'], code)
            if code == 'http_503':
                self.assertIn('Gemini 서비스가 일시적으로', result['summary'])
            self.assertNotIn('test-secret', ' '.join(logs.output))

    def test_empty_malformed_and_truncated_responses(self):
        for reason, content in [('STOP', 'not json'), ('STOP', ''), ('MAX_TOKENS', '{}')]:
            response = types.GenerateContentResponse(candidates=[types.Candidate(
                finish_reason=reason, content=types.Content(parts=[types.Part(text=content)]))])
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-secret'}), patch('app.ai_review.client.genai.Client') as factory:
                factory.return_value.__enter__.return_value.models.generate_content.return_value = response
                with self.assertRaises(ReviewError):
                    GeminiClient().review(self.evidence)

    def test_diagnostic_logs_describe_request_without_input_or_secrets(self):
        self.plan['description'] = 'private-program-text'
        error = errors.ClientError(400, {'error': {'message': 'Unknown name responseFormat private-program-text test-secret'}})
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-secret'}), patch('app.ai_review.client.genai.Client') as factory, self.assertLogs('app.ai_review', level='INFO') as logs:
            factory.return_value.__enter__.return_value.models.generate_content.side_effect = error
            result = review_plan(self.plan, [], self.stats, timezone.now())
        output = '\n'.join(logs.output)
        self.assertIn('sdk_request', output)
        self.assertIn('content_bytes=', output)
        self.assertIn('schema=', output)
        self.assertIn('unsupported_field', output)
        self.assertNotIn('private-program-text', output)
        self.assertNotIn('test-secret', output)
        self.assertEqual(result['error_code'], 'http_400')
