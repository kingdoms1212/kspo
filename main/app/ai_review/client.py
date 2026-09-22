from typing import Protocol
import json
import logging
from importlib.metadata import version
from time import perf_counter
import os
import re
import httpx
from google import genai
from google.genai import errors, types
from django.conf import settings
from .prompts import SYSTEM_INSTRUCTION
from .schemas import response_schema


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


class ReviewError(Exception):
    """Only safe error codes, never provider messages or credentials."""


class ReviewClient(Protocol):
    def review(self, evidence: dict) -> dict:
        """검증된 입력을 받아 summary, findings, suggestions, limitations를 반환합니다."""
        ...


class GeminiClient:
    """공식 google-genai SDK로 구조화 응답을 요청합니다."""

    def __init__(self, request_id='standalone', instruction=None, schema=None):
        self.request_id = request_id
        self.instruction = instruction or SYSTEM_INSTRUCTION
        self.schema = schema

    def review(self, evidence: dict) -> dict:
        key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not key:
            raise ReviewError('missing_key')
        model = settings.GEMINI_MODEL
        if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', model):
            raise ReviewError('invalid_model')
        contents = json.dumps(evidence, ensure_ascii=False)
        schema = self.schema or response_schema(evidence)
        logger.info('AI_REVIEW sdk_request request_id=%s sdk=%s model=%s api_version=v1beta timeout_ms=%d attempts=11 max_retries=10 afc=False mime=application/json max_output_tokens=4096 content_bytes=%d evidence_fields=%s plan_fields=%s schema=%s',
                    self.request_id, version('google-genai'), model, int(settings.GEMINI_TIMEOUT_SECONDS * 1000),
                    len(contents.encode('utf-8')), ','.join(sorted(evidence)),
                    ','.join(sorted(evidence.get('plan', {}))), json.dumps(schema, ensure_ascii=False))
        started = perf_counter()
        try:
            with genai.Client(api_key=key, vertexai=False, http_options=types.HttpOptions(
                    api_version='v1beta', timeout=int(settings.GEMINI_TIMEOUT_SECONDS * 1000),
                    retry_options=types.HttpRetryOptions(attempts=11, initial_delay=1, max_delay=5,
                                                         exp_base=2, jitter=1,
                                                         http_status_codes=[429, 500, 502, 503, 504]))) as client:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.instruction,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        max_output_tokens=4096,
                        response_mime_type='application/json',
                        response_json_schema=schema))
            logger.info('AI_REVIEW sdk_response request_id=%s seconds=%.3f candidates=%d finish_reason=%s',
                        self.request_id, perf_counter() - started, len(response.candidates or []),
                        response.candidates[0].finish_reason if response.candidates else 'none')
            if not response.candidates or response.candidates[0].finish_reason != types.FinishReason.STOP:
                raise ReviewError('incomplete_response')
            content = response.text
            if not content or not content.strip():
                raise ReviewError('empty_response')
            if len(content.encode('utf-8')) > 262144:
                raise ReviewError('oversize_response')
            return json.loads(content)
        # [SG003] AI기능 연동 시 예외처리 보완 — 공급자·통신·응답 오류를 안전한 오류 코드로 변환합니다.
        except errors.APIError as error:
            logger.warning('AI_REVIEW sdk_error request_id=%s http_status=%s reasons=%s seconds=%.3f',
                           self.request_id, error.code, ','.join(error_diagnostic(error)), perf_counter() - started)
            raise ReviewError('rate_limit' if error.code == 429 else f'http_{error.code}') from None
        except (httpx.TimeoutException, TimeoutError):
            raise ReviewError('timeout') from None
        except httpx.RequestError:
            raise ReviewError('network') from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ReviewError('invalid_json') from None


class DummyGeminiClient:
    """UI·인쇄·보관 흐름 확인용이며 실제 적합성 판단을 수행하지 않습니다."""

    def review(self, evidence: dict) -> dict:
        plan = evidence['plan']
        return {
            'summary': f"{plan['region']} 지역의 {plan['sport']} 프로그램 검토 표시 예시입니다. 실제 AI 평가가 아닙니다.",
            'findings': [
                {'title': '지역·종목', 'status': '판단 자료 부족',
                 'comment': '선택 지역의 이용현황과 종목 통계를 검토 입력에 포함했습니다. 적합성 판단은 실제 연동 후 제공됩니다.'},
                {'title': '시설', 'status': '판단 자료 부족',
                 'comment': ('선택한 시설의 정보가 포함됐습니다. 실제 이용 가능 시간과 수용인원은 별도 확인이 필요합니다.'
                             if evidence['facilities'] else '시설 미지정 상태입니다. 운영 장소와 종목별 필요 설비를 먼저 확인해 주세요.')},
                {'title': '운영계획', 'status': '판단 자료 부족',
                 'comment': '대상·기간·인원·수강료·프로그램 설명을 검토 입력에 포함했습니다. 내용에 대한 자동 판단은 수행하지 않았습니다.'},
            ],
            'suggestions': ['참여 대상과 회차별 활동 내용을 구체화해 주세요.',
                            '시설 예약 가능 여부와 운영 인력을 확인해 주세요.',
                            '모집인원과 운영기간에 맞는 예산을 확인해 주세요.'],
            'limitations': ['더미 응답이므로 적합성 심사나 승인 근거로 사용할 수 없습니다.',
                            '이용현황만으로 향후 수요나 모집 성공을 확정할 수 없습니다.'],
        }
