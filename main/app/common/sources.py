"""원본 CSV 네 개의 이름을 한 곳에서 정한다.

같은 파일 이름이 다섯 모듈에 따로 적혀 있었다. 배치는 `data/<이름>.csv`를
읽어 서울 추출본을 쓰고, 네 저장소는 `data/Batch/<줄기>_seoul.csv`를 읽는다.
원본 이름을 바꾸려면 다섯 곳을 모두 찾아야 했고, 하나를 놓치면 빈 화면으로만
드러났다.

여기에는 원본 이름만 적는다. 서비스 파일(`_seoul`)과 직전 실행 보관본
(`_seoul_temp`)은 배치의 명명 규칙대로 파생되므로, 쓰는 쪽과 읽는 쪽의
이름이 어긋날 수 없다.

Django를 import하지 않는다. `manage.py`가 `django.setup()` 이전에 배치를
부르기 때문이다.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    """원본 한 종류: `data/`의 파일과 서울 행을 가리는 두 열."""

    filename: str
    code_column: str
    name_column: str

    @property
    def final_filename(self) -> str:
        """화면이 읽는 서비스 파일 이름."""
        return f"{Path(self.filename).stem}_seoul.csv"

    @property
    def previous_filename(self) -> str:
        """교체 실패에 대비해 남기는 직전 실행 보관본 이름."""
        return f"{Path(self.filename).stem}_seoul_temp.csv"


PROGRAM = SourceSpec("공공체육시설 프로그램 정보.csv", "CTPRVN_CD", "CTPRVN_NM")
USAGE = SourceSpec("스포츠강좌이용권 이용현황 정보.csv", "CTPRVN_CD", "CTPRVN_NM")
FACILITY = SourceSpec("전국체육시설현황 데이터.csv", "CTPRVN_CD", "CTPRVN_NM")
TRANSIT = SourceSpec("체육시설 인접 대중교통 정보.csv", "ALSFC_CTPRVN_CD", "ALSFC_CTPRVN_NM")

# 배치는 이 순서대로 네 파일을 처리하고, 각 화면은 이름으로 하나씩 가져간다.
SOURCE_SPECS = (PROGRAM, USAGE, FACILITY, TRANSIT)
