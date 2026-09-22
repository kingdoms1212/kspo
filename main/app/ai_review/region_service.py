"""Region analysis and generation-keyed cache, independent of HTTP views."""
import hashlib
import json
import logging
import os
import pickle
from uuid import uuid4
from django.conf import settings
from django.core.cache.backends.filebased import FileBasedCache
from .contracts import AIRequest
from .errors import ReviewError
from .factory import create_provider, get_config
from .schemas import TEXT, TEXT_LIST
from .prompts import REGION_INSTRUCTION
from .services import _review_slot
from ..common.versioned_csv import source_version, DataGenerationPending
from ..dashboard.services import dashboard_data, selected_districts

logger = logging.getLogger(__name__)

# [SG003] AI기능 연동 시 예외처리 보완 — 공백·불완전 응답과 손상 캐시를 거부합니다.
def validate_region_result(result):
    if not isinstance(result, dict) or set(result) != {'summary', 'features', 'considerations'}:
        raise ValueError('invalid response')
    def valid_text(value):
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000
    if not valid_text(result['summary']): raise ValueError('invalid summary')
    for field in ('features', 'considerations'):
        if not isinstance(result[field], list) or len(result[field]) > 8 or not all(valid_text(v) for v in result[field]):
            raise ValueError('invalid list')
    return result


def analyze_region(district_value):
    districts = selected_districts(district_value)
    if len(districts) > 25 or any(len(d) > 20 for d in districts):
        return {'error': '지역 선택을 확인해 주세요.'}, 400
    config = get_config()
    acquired = False
    request_id = uuid4().hex[:12]
    stage = 'evidence'
    # [SG003] AI기능 연동 시 예외처리 보완 — 키 값 대신 프로세스의 설정 인식 여부만 기록합니다.
    logger.info('AI_REGION start request_id=%s mode=%s provider=%s model=%s key_configured=%s on_render=%s',
                request_id, config.mode, config.provider, config.model,
                config.key_configured,
                os.environ.get('RENDER', '').lower() == 'true')
    try:
        generation = source_version(settings.DATA_FILES['usage'])
        stats = dashboard_data('서울', ','.join(districts))
        options = stats.get('region_district_options', {}).get('서울', [])
        if any(d not in options for d in districts):
            return {'error': '지역 선택을 확인해 주세요.'}, 400
        evidence = {'region': '서울', 'districts': districts, **{k: stats[k] for k in
            ('facilities', 'courses', 'requests', 'sport_rows', 'period')}}
        key = hashlib.sha256(json.dumps([generation, evidence, config.provider, config.model, config.mode, 'region-v2'], sort_keys=True, default=str).encode()).hexdigest()
        # [SG003] AI기능 연동 시 예외처리 보완 — 캐시 장애로 정상 분석 결과가 유실되지 않도록 처리합니다.
        cache = None
        try:
            cache = FileBasedCache(str(settings.BASE_DIR / '.ai-cache'), {'TIMEOUT': 86400, 'OPTIONS': {'MAX_ENTRIES': 200}})
            cached = cache.get(key)
            if cached is not None:
                validate_region_result(cached['result'])
                if source_version(settings.DATA_FILES['usage']) != generation:
                    raise DataGenerationPending('generation changed')
                logger.info('AI_REGION cache_hit request_id=%s', request_id)
                return {'result': cached['result'], 'cached': True}, 200
        except (OSError, ValueError, TypeError, KeyError, EOFError, pickle.UnpicklingError):
            logger.warning('AI_REGION cache_read_failed request_id=%s', request_id)
        stage = 'api'
        acquired = _review_slot.acquire(blocking=False)
        if not acquired: return {'error': '다른 AI 분석이 진행 중입니다. 잠시 후 다시 시도해 주세요.'}, 429
        schema = {'type': 'object', 'properties': {'summary': TEXT, 'features': TEXT_LIST, 'considerations': TEXT_LIST},
                  'required': ['summary', 'features', 'considerations'], 'additionalProperties': False}
        client = create_provider(config)
        response = client.generate(AIRequest('region_summary', REGION_INSTRUCTION, evidence, schema, request_id))
        result = response.data
        stage = 'validation'
        validate_region_result(result)
        # Do not publish results under a changed generation.
        if source_version(settings.DATA_FILES['usage']) != generation: raise DataGenerationPending('generation changed')
        payload = {'result': result, 'cached': False}
        if cache is not None:
            try:
                cache.set(key, payload)
            except OSError:
                logger.warning('AI_REGION cache_write_failed request_id=%s', request_id)
        logger.info('AI_REGION completed request_id=%s', request_id)
        return payload, 200
    # [SG003] AI기능 연동 시 예외처리 보완 — 지역 분석 실패를 안전한 응답과 진단 로그로 처리합니다.
    except Exception as error:
        logger.warning('AI_REGION unavailable request_id=%s stage=%s code=%s error_type=%s',
                       request_id, stage, str(error) if isinstance(error, ReviewError) else 'validation_or_internal', type(error).__name__)
        return {'error': '현황 해석을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.'}, 503
    finally:
        if acquired: _review_slot.release()
