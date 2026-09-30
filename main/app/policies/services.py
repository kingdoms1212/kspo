# 서정길 [SJG008] 주요 정책 보기 — 백엔드 수집·캐시 및 프론트 다이얼로그
"""Presentation shape for the policy listing."""
from . import models


def policy_panel(force=False):
    """What the dialog and the standalone page both render."""
    result = models.policies(force=force)
    return {**result, 'count': len(result['policies'])}
