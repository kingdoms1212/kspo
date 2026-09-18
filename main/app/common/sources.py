"""화면과 배치가 함께 사용하는 원본 CSV 정의를 제공한다.

CSV 열 구성과 지역별 파일명 규칙은 지역 배치 모듈에서 한 번만 정의한다.
화면 저장소는 이 호환 모듈을 통해 같은 객체를 가져오므로, 배치가 생성하는
파일명과 화면이 읽는 파일명이 서로 달라지지 않는다.
"""

from ..Batch.regional_csv_batch import SOURCE_SPECS, SourceSpec


PROGRAM, USAGE, FACILITY, TRANSIT = SOURCE_SPECS

__all__ = (
    "SourceSpec",
    "SOURCE_SPECS",
    "PROGRAM",
    "USAGE",
    "FACILITY",
    "TRANSIT",
)
