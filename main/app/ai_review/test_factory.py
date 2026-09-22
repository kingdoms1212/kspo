import builtins
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from .contracts import AIRequest, AIResponse
from .errors import ReviewError
from .factory import create_provider, get_config
from .schemas import normalize_analysis, response_schema
from .services import review_plan, build_evidence

@override_settings(AI_MODE='', AI_PROVIDER='', AI_MODEL='', AI_TIMEOUT_SECONDS=None,
                   AI_MAX_RETRIES=10, AI_REVIEW_MODE='gemini', GEMINI_MODEL='gemini-legacy',
                   GEMINI_TIMEOUT_SECONDS=25)
class FactoryTests(SimpleTestCase):
    def test_legacy_settings_remain_compatible(self):
        config = get_config()
        self.assertEqual((config.mode, config.provider, config.model, config.timeout, config.retries),
                         ('live', 'gemini', 'gemini-legacy', 25, 10))
        with override_settings(AI_REVIEW_MODE='dummy'):
            self.assertEqual(get_config().mode, 'dummy')

    @override_settings(AI_MODE='live', AI_PROVIDER='other', AI_MODEL='other-model', AI_TIMEOUT_SECONDS=12, AI_MAX_RETRIES=0)
    def test_new_settings_override_legacy_without_silent_fallback(self):
        config = get_config()
        self.assertEqual((config.provider, config.model, config.timeout, config.retries), ('other', 'other-model', 12, 0))
        with self.assertRaisesRegex(ReviewError, 'unsupported_provider'):
            create_provider(config)

    @override_settings(AI_MODE='dummy')
    def test_dummy_uses_common_schema_without_importing_sdk(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.startswith(('google', 'httpx')): raise AssertionError('SDK imported')
            return original(name, *args, **kwargs)
        evidence = build_evidence({'sport': '수영'}, [], {'sports': [('수영', 1)]})
        with patch('builtins.__import__', side_effect=guarded):
            provider = create_provider()
            response = provider.generate(AIRequest('plan_review', '', evidence, response_schema(evidence), 'test'))
        self.assertEqual(response.provider, 'dummy')
        self.assertIsNone(normalize_analysis(response.data, evidence)['overall_score'])
        region = provider.generate(AIRequest('region_summary', '', {}, {}, 'test'))
        self.assertEqual(set(region.data), {'summary', 'features', 'considerations'})

    def test_missing_sdk_is_safe_error(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'private'}), patch('app.ai_review.factory.import_module', side_effect=ImportError):
            with self.assertRaisesRegex(ReviewError, 'sdk_unavailable'):
                create_provider()

    def test_plan_service_accepts_another_provider(self):
        class OtherProvider:
            def generate(self, request):
                return AIResponse({'summary': '다른 공급자 결과',
                    'evaluations': {key: {'score': 70, 'reason': '근거 기반 의견', 'evidence_keys': refs}
                        for key, refs in request.evidence['available_criteria'].items()},
                    'strengths': [], 'risks': [], 'recommendations': [], 'limitations': []}, 'other', 'other-model')
        with patch('app.ai_review.services.create_provider', return_value=OtherProvider()):
            result = review_plan({'sport': '수영'}, [], {'sports': [('수영', 1)]}, timezone.now())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual((result['provider'], result['model'], result['overall_score']), ('other', 'other-model', 70))
