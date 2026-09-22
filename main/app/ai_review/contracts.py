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
