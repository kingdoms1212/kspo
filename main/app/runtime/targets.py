"""사전 적재 대상 등록. 기능 추가 시 이 조립 지점에 공개 함수만 등록한다."""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CsvWarmupTarget:
    filename: str
    refresh: Callable[[], bool]
    set_background_refresh: Callable[[bool], None]


def csv_warmup_targets():
    # Django 초기화 후에만 기능별 저장소를 가져온다.
    from app.programs import models as programs
    from app.facilities import models as facilities
    from app.dashboard import models as usage

    # 교통 상세 색인은 목록 조회에 필요하지 않으므로 지연 적재를 유지한다.
    return (
        CsvWarmupTarget(programs.PROGRAM_FILE, programs.refresh_snapshot, programs.set_background_refresh),
        CsvWarmupTarget(facilities.FACILITY_FILE, facilities.refresh_snapshot, facilities.set_background_refresh),
        CsvWarmupTarget(usage.USAGE_FILE, usage.refresh_snapshot, usage.set_background_refresh),
    )
