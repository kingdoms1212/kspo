import logging
from datetime import date, datetime

from django.conf import settings

from .client import DummyGeminiClient, GeminiClient, ReviewClient

logger = logging.getLogger(__name__)


def build_evidence(plan, selected, statistics):
    """보고서와 같은 통계를 사용하며 원본 전체나 연락처를 전송하지 않습니다."""
    fields = ('name', 'region', 'district', 'sport', 'target', 'start', 'end',
              'capacity', 'fee', 'fee_unit', 'description')
    values = {key: plan.get(key) for key in fields}
    values = {key: value.isoformat() if isinstance(value, (date, datetime)) else value
              for key, value in values.items()}
    return {
        'plan': values,
        'facilities': [dict(name=row.name, address=row.address,
                            type=row.facility_type, state=row.state) for row in selected],
        'statistics': {key: statistics.get(key) for key in ('requests', 'courses', 'facilities')},
        'sport_requests': dict(statistics.get('sports', [])).get(plan['sport']),
    }


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
    mode = getattr(settings, 'AI_REVIEW_MODE', 'dummy')
    metadata = {'mode': mode, 'created': created, 'provider': 'Gemini',
                'model': 'dummy-v1', 'criteria_version': '1'}
    try:
        client: ReviewClient = DummyGeminiClient() if mode == 'dummy' else GeminiClient()
        result = validate_response(client.review(build_evidence(plan, selected, statistics)))
        return {**result, **metadata, 'status': 'completed'}
    except Exception:
        logger.warning('AI review unavailable: mode=%s', mode)
        return {**metadata, 'status': 'unavailable',
                'summary': 'AI 검토 결과를 가져오지 못했습니다. 기본 계획서는 그대로 이용할 수 있습니다.'}
