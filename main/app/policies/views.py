# 서정길 [SJG008] 주요 정책 보기 — 백엔드 수집·캐시 및 프론트 다이얼로그
"""Policy listing controller: dialog fragment or standalone page."""
from ..common.partials import render_screen
from .services import policy_panel


def policies(request):
    context = {'page': 'policies', **policy_panel()}
    return render_screen(request, 'policies/index.html', 'policies/_list.html', context)
