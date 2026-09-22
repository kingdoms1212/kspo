"""Explicit AI actions; signed plan reviews and generation-keyed region summaries."""
import hashlib
import json
from datetime import datetime
from django.core import signing
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from ..ai_review.region_service import analyze_region
from ..ai_review.services import review_plan
from ..common.versioned_csv import DataGenerationPending
from .planning import PlanForm

SALT = 'plan-ai-review-v1'

def fingerprint(form):
    data = {k: v for k, v in form.cleaned_data.items() if k != 'ai_review'}
    data['selected_ids'] = sorted(row.id for row in form.selected)
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()

# [SG003] AI기능 연동 시 예외처리 보완 — 서명 결과의 구조·입력 일치 여부를 검증합니다.
def review_from_token(token, form):
    if not token or len(token) > 100000: raise ValueError('invalid token')
    data = signing.loads(token, salt=SALT, max_age=3600)
    if not isinstance(data, dict) or data.get('fingerprint') != fingerprint(form):
        raise ValueError('changed plan')
    result = data.get('review')
    if not isinstance(result, dict) or result.get('status') != 'completed':
        raise ValueError('invalid review')
    result = dict(result)
    result['created'] = datetime.fromisoformat(result['created'])
    return result


@never_cache
@require_POST
def plan_review(request):
    form = PlanForm(request.POST)
    try:
        if not form.is_valid(): return JsonResponse({'errors': form.errors}, status=400)
    # [SG003] AI기능 연동 시 예외처리 보완 — CSV 갱신 중에도 JSON 오류 안내를 반환합니다.
    except (DataGenerationPending, OSError):
        return JsonResponse({'error': '기초 자료를 갱신 중입니다. 잠시 후 다시 시도해 주세요.'}, status=503)
    result = review_plan(form.cleaned_data, form.selected, form.statistics, timezone.localtime())
    html = render_to_string('dashboard/_plan_ai_review.html', {'ai_review': result})
    token = ''
    if result['status'] == 'completed':
        value = {**result, 'created': result['created'].isoformat()}
        token = signing.dumps({'fingerprint': fingerprint(form), 'review': value}, salt=SALT, compress=True)
    return JsonResponse({'html': html, 'token': token})

@never_cache
@require_POST
def region_review(request):
    payload, status = analyze_region(request.POST.get('district', ''))
    return JsonResponse(payload, status=status)
