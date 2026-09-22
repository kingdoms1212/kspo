from ..contracts import AIRequest, AIResponse
from ..errors import ReviewError

class DummyProvider:
    """Same response contracts as live providers, without SDK/network access."""
    def generate(self, request: AIRequest) -> AIResponse:
        if request.task == 'region_summary':
            data = {'summary': '데모: 선택 지역 현황 요약입니다. 실제 AI 분석이 아닙니다.',
                    'features': ['등록된 시설·강좌와 신청 실적을 참고합니다.'],
                    'considerations': ['신청 실적은 고유 이용자나 지역 전체 수요가 아닙니다.']}
        elif request.task == 'plan_review':
            data = {'summary': '데모: 프로그램 검토 표시 예시입니다. 실제 AI 평가가 아닙니다.',
                    'evaluations': {key: {'score': None, 'reason': '데모 모드로 실제 평가를 수행하지 않았습니다.',
                        'evidence_keys': []} for key in request.evidence['available_criteria']},
                    'strengths': [], 'risks': [], 'recommendations': ['시설 이용 가능 시간과 운영 내용을 확인하세요.'],
                    'limitations': ['데모 결과는 심사나 승인 근거로 사용할 수 없습니다.']}
        else: raise ReviewError('unsupported_task')
        return AIResponse(data, 'dummy', 'dummy-v2')
