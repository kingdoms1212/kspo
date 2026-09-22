"""Configuration and lazy provider selection. SDK imports stay inside adapters."""
import os
from importlib import import_module
from dataclasses import dataclass
from django.conf import settings
from .contracts import AIProvider
from .errors import ReviewError

# Register a provider module and its dedicated secret environment variable here.
PROVIDERS = {
    'gemini': ('app.ai_review.providers.gemini', 'GeminiProvider', 'GEMINI_API_KEY'),
}

@dataclass(frozen=True)
class AIConfig:
    mode: str
    provider: str
    model: str
    timeout: float
    retries: int

    @property
    def key_configured(self):
        spec = PROVIDERS.get(self.provider)
        name = spec[2] if spec else None
        return bool(name and os.environ.get(name, '').strip())


def get_config():
    legacy = settings.AI_REVIEW_MODE
    mode = settings.AI_MODE or ('dummy' if legacy == 'dummy' else 'live' if legacy == 'gemini' else legacy)
    provider = settings.AI_PROVIDER or 'gemini'
    model = settings.AI_MODEL or (settings.GEMINI_MODEL if provider == 'gemini' else '')
    timeout = settings.AI_TIMEOUT_SECONDS if settings.AI_TIMEOUT_SECONDS is not None else settings.GEMINI_TIMEOUT_SECONDS
    return AIConfig(mode, provider, model, timeout, settings.AI_MAX_RETRIES)


def create_provider(config=None) -> AIProvider:
    config = config or get_config()
    if config.mode == 'dummy':
        from .providers.dummy import DummyProvider
        return DummyProvider()
    if config.mode != 'live': raise ReviewError('invalid_mode')
    spec = PROVIDERS.get(config.provider)
    if spec is None: raise ReviewError('unsupported_provider')
    if not config.model: raise ReviewError('invalid_model')
    # [SG003] AI기능 연동 시 예외처리 보완 — 선택된 SDK만 로딩하고 누락을 안전하게 처리합니다.
    if not config.key_configured: raise ReviewError('missing_key')
    try:
        provider_class = getattr(import_module(spec[0]), spec[1])
    except ImportError:
        raise ReviewError('sdk_unavailable') from None
    return provider_class(config)
