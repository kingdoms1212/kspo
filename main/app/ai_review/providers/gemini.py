import json
import logging
from importlib.metadata import version
from time import perf_counter
import os
import re
import httpx
from google import genai
from google.genai import errors, types
from ..contracts import AIRequest, AIResponse
from ..errors import ReviewError


logger = logging.getLogger(__name__)


def error_diagnostic(error):
    # 공급자가 입력을 되돌려 줄 수 있어 원문 대신 알려진 원인만 기록합니다.
    message = str(getattr(error, 'message', '')).lower()
    patterns = {
        'overloaded': ('overload', 'high demand'),
        'invalid_api_key': ('api key not valid', 'api_key_invalid', 'invalid api key'),
        'model_not_found': ('model is not found', 'model not found', 'is not found for api version'),
        'unsupported_field': ('unknown name', 'unknown field', 'unrecognized field'),
        'schema_rejected': ('schema',),
        'quota_exceeded': ('quota', 'resource exhausted'),
        'permission_denied': ('permission denied', 'permission_denied'),
        'service_unavailable': ('unavailable',),
    }
    return [code for code, phrases in patterns.items() if any(p in message for p in phrases)] or ['unclassified']


class GeminiProvider:
    """Gemini SDK adapter; owns SDK-specific formats and retry mapping."""
    def __init__(self, config):
        self.config = config

    def generate(self, request: AIRequest) -> AIResponse:
        evidence = request.evidence
        key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not key:
            raise ReviewError('missing_key')
        model = self.config.model
        if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', model):
            raise ReviewError('invalid_model')
        contents = json.dumps(evidence, ensure_ascii=False)
        schema = request.schema
        logger.info('AI_REVIEW sdk_request request_id=%s sdk=%s model=%s api_version=v1beta timeout_ms=%d attempts=%d max_retries=%d afc=False mime=application/json max_output_tokens=4096 content_bytes=%d evidence_fields=%s plan_fields=%s schema=%s',
                    request.request_id, version('google-genai'), model, int(self.config.timeout * 1000),
                    self.config.retries + 1, self.config.retries, len(contents.encode('utf-8')), ','.join(sorted(evidence)),
                    ','.join(sorted(evidence.get('plan', {}))), json.dumps(schema, ensure_ascii=False))
        started = perf_counter()
        try:
            with genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(
                    api_version='v1beta', timeout=int(self.config.timeout * 1000),
                    retry_options=types.HttpRetryOptions(attempts=self.config.retries + 1, initial_delay=1, max_delay=5,
                                                         exp_base=2, jitter=1,
                                                         http_status_codes=[429, 500, 502, 503, 504]))) as client:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=request.instruction,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        max_output_tokens=4096,
                        response_mime_type='application/json',
                        response_json_schema=schema))
            logger.info('AI_REVIEW sdk_response request_id=%s seconds=%.3f candidates=%d finish_reason=%s',
                        request.request_id, perf_counter() - started, len(response.candidates or []),
                        response.candidates[0].finish_reason if response.candidates else 'none')
            if not response.candidates or response.candidates[0].finish_reason != types.FinishReason.STOP:
                raise ReviewError('incomplete_response')
            content = response.text
            if not content or not content.strip():
                raise ReviewError('empty_response')
            if len(content.encode('utf-8')) > 262144:
                raise ReviewError('oversize_response')
            data = json.loads(content)
            if not isinstance(data, dict): raise ReviewError('invalid_json')
            return AIResponse(data, 'gemini', response.model_version or model)
        # [SG003] AI기능 연동 시 예외처리 보완 — 공급자·통신·응답 오류를 안전한 오류 코드로 변환합니다.
        except errors.APIError as error:
            logger.warning('AI_REVIEW sdk_error request_id=%s http_status=%s reasons=%s seconds=%.3f',
                           request.request_id, error.code, ','.join(error_diagnostic(error)), perf_counter() - started)
            raise ReviewError('rate_limit' if error.code == 429 else f'http_{error.code}') from None
        except (httpx.TimeoutException, TimeoutError):
            raise ReviewError('timeout') from None
        except httpx.RequestError:
            raise ReviewError('network') from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ReviewError('invalid_json') from None
