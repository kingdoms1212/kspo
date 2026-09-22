import logging
import os
from datetime import date, datetime
from threading import BoundedSemaphore
from time import perf_counter
from uuid import uuid4

from django.conf import settings

from .client import DummyGeminiClient, GeminiClient, ReviewClient
from .client import ReviewError
from .schemas import normalize_analysis

logger = logging.getLogger(__name__)
_review_slot = BoundedSemaphore(1)


def build_evidence(plan, selected, statistics):
    """보고서와 같은 통계를 사용하며 원본 전체나 연락처를 전송하지 않습니다."""
    fields = ('name', 'region', 'district', 'sport', 'target', 'start', 'end',
              'capacity', 'fee', 'fee_unit', 'description')
    values = {key: plan.get(key) for key in fields}
    values = {key: value.isoformat() if isinstance(value, (date, datetime)) else value
              for key, value in values.items()}
    evidence = {
        'plan': values,
        'facilities': [dict(name=row.name, address=row.address,
                            type=row.facility_type, state=row.state) for row in selected],
        'statistics': {key: statistics.get(key) for key in ('requests', 'courses', 'facilities')},
        'sport_requests': dict(statistics.get('sports', [])).get(plan['sport']),
    }
    sport = next((row for row in statistics.get('sport_rows', []) if row['name'] == plan['sport']), {})
    evidence.update(selected_sport_statistics={key: sport.get(key) for key in ('requests', 'courses', 'facilities')},
        period=statistics.get('period', []),
        source='sports_voucher_usage: applications and registered courses, not population-wide demand',
        metric_notes='Facility and course counts come from the voucher usage dataset, not a complete facility census. Fees are per-person charges, not an operating budget.')
    if getattr(settings, 'AI_REVIEW_INCLUDE_TRANSIT', False) and selected:
        from ..facilities.services import facility_transit
        evidence['transport'] = []
        for row in selected:
            transit = facility_transit(row) or {}
            evidence['transport'].append({'facility': row.name, **{key: transit.get(key) for key in
                ('has_records', 'nearest_metres', 'nearest_minutes', 'reason', 'source')}})
    evidence['available_criteria'] = {
        'population_fit': [],
        'sports_demand': ['sport_requests'] if evidence['sport_requests'] is not None else [],
        'facility_supply': ['selected_sport_statistics'] if sport.get('facilities') is not None else [],
        'facility_fit': ['facilities'] if selected else [],
        'transport_accessibility': ['transport'] if any(row.get('has_records') for row in evidence.get('transport', [])) else [],
        'welfare_need': [], 'budget_feasibility': [],
    }
    evidence['available_criteria'] = {key: refs for key, refs in evidence['available_criteria'].items() if refs}
    def omit_missing(value):
        if isinstance(value, dict):
            return {key: omit_missing(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            return [omit_missing(item) for item in value]
        return value
    return omit_missing(evidence)


def validate_response(data):
    """불완전한 응답이 보고서 렌더링을 깨뜨리지 않도록 제한합니다."""
    def text(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError('Invalid review text')
        return value

    result = {'summary': text(data['summary'])}
    findings = data['findings']
    if not isinstance(findings, list) or not 1 <= len(findings) <= 8:
        raise ValueError('Invalid findings')
    result['findings'] = []
    for item in findings:
        if item['status'] not in ('적합 의견', '보완 필요', '판단 자료 부족'):
            raise ValueError('Invalid status')
        result['findings'].append({key: text(item[key]) for key in ('title', 'status', 'comment')})
    for key in ('suggestions', 'limitations'):
        if not isinstance(data[key], list) or not 1 <= len(data[key]) <= 8:
            raise ValueError('Invalid list')
        result[key] = [text(value) for value in data[key]]
    return result


def review_plan(plan, selected, statistics, created):
    mode = settings.AI_REVIEW_MODE
    metadata = {'mode': mode, 'created': created, 'provider': 'Gemini',
                'model': 'dummy-v1' if mode == 'dummy' else settings.GEMINI_MODEL, 'criteria_version': '3'}
    started = perf_counter()
    acquired = False
    request_id = uuid4().hex[:12]
    stage = 'configuration'
    logger.info('AI_REVIEW start request_id=%s mode=%s model=%s key_configured=%s timeout=%s',
                request_id, mode, metadata['model'], bool(os.environ.get('GEMINI_API_KEY', '').strip()),
                settings.GEMINI_TIMEOUT_SECONDS)
    try:
        if mode not in ('dummy', 'gemini'):
            raise ReviewError('invalid_mode')
        if mode == 'gemini' and not os.environ.get('GEMINI_API_KEY', '').strip():
            raise ReviewError('missing_key')
        acquired = _review_slot.acquire(blocking=False)
        if not acquired:
            raise ReviewError('busy')
        client: ReviewClient = DummyGeminiClient() if mode == 'dummy' else GeminiClient(request_id=request_id)
        stage = 'evidence'
        evidence = build_evidence(plan, selected, statistics)
        logger.info('AI_REVIEW request request_id=%s criteria=%s facilities=%d seconds=%.3f',
                    request_id, ','.join(evidence['available_criteria']), len(selected), perf_counter() - started)
        stage = 'api'
        api_started = perf_counter()
        response = client.review(evidence)
        logger.info('AI_REVIEW response request_id=%s seconds=%.3f', request_id, perf_counter() - api_started)
        stage = 'validation'
        result = validate_response(response) if mode == 'dummy' else normalize_analysis(response, evidence)
        logger.info('AI_REVIEW completed request_id=%s mode=%s scored_count=%s seconds=%.3f',
                    request_id, mode, result.get('scored_count'), perf_counter() - started)
        return {**result, **metadata, 'status': 'completed'}
    # [SG003] AI기능 연동 시 예외처리 보완 — AI 실패 시에도 기본 계획서를 이용할 수 있도록 처리합니다.
    except Exception as error:
        code = str(error) if isinstance(error, ReviewError) else 'validation_or_internal'
        logger.warning('AI_REVIEW unavailable request_id=%s mode=%s stage=%s code=%s error_type=%s seconds=%.3f',
                       request_id, mode, stage, code, type(error).__name__, perf_counter() - started)
        return {**metadata, 'status': 'unavailable',
                'error_code': code,
                'summary': ('Gemini 서비스가 일시적으로 응답할 수 없습니다. 잠시 후 다시 시도해 주세요. 기본 계획서는 그대로 이용할 수 있습니다.' if code == 'http_503' else
                            'AI 분석 설정이 준비되지 않았습니다. 기본 계획서는 그대로 이용할 수 있습니다.' if code == 'missing_key' else
                            'AI 검토 결과를 가져오지 못했습니다. 기본 계획서는 그대로 이용할 수 있습니다. 잠시 후 다시 시도해 주세요.')}
    finally:
        if acquired:
            _review_slot.release()
