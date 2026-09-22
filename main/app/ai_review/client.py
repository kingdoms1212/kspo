from typing import Protocol


class ReviewClient(Protocol):
    def review(self, evidence: dict) -> dict:
        """검증된 입력을 받아 summary, findings, suggestions, limitations를 반환합니다."""
        ...


class GeminiClient:
    """실제 Gemini 전송은 아직 구현하지 않습니다."""

    def review(self, evidence: dict) -> dict:
        raise NotImplementedError('Gemini API 연동 준비 중입니다.')


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
