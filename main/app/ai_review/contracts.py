# 서정길 [SJG003] AI 공통 연동 — 백엔드 공급자 호출·응답 검증
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class AIRequest:
    task: str
    instruction: str
    evidence: dict
    schema: dict
    request_id: str

@dataclass(frozen=True)
class AIResponse:
    data: dict
    provider: str
    model: str

class AIProvider(Protocol):
    def generate(self, request: AIRequest) -> AIResponse: ...
