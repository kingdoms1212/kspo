# 서정길 [SJG003] AI 공통 연동 — 백엔드 공급자 호출·응답 검증
class ReviewError(Exception):
    """Safe application error code; never include provider messages or credentials."""
