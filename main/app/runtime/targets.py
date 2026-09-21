"""사전 적재 대상 등록. 기능 추가 시 이 조립 지점에 공개 함수만 등록한다."""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CsvWarmupTarget:
    key: str
    label: str
    filename: str
    refresh: Callable[[], bool]
    set_background_refresh: Callable[[bool], None]
    is_ready: Callable[[], bool]


def csv_warmup_targets():
    # Django 초기화 후에만 기능별 저장소를 가져온다.
    from app.programs import models as programs
    from app.facilities import models as facilities
    from app.dashboard import models as usage

    # 교통 상세 색인은 목록 조회에 필요하지 않으므로 지연 적재를 유지한다.
    # 준비 상태 판정에도 넣지 않는다. 넣으면 시설 상세를 누를 때마다 화면이
    # 미준비로 보인다.
    return (
        # 가벼운 자료부터 적재해 해당 화면이 먼저 열리게 한다. 전체 소요는
        # 같지만 시설·대시보드가 프로그램 적재를 기다리지 않는다.
        CsvWarmupTarget('facilities', '시설 현황', facilities.FACILITY_FILE,
                        facilities.refresh_snapshot, facilities.set_background_refresh,
                        facilities.snapshot_loaded),
        CsvWarmupTarget('usage', '이용현황', usage.USAGE_FILE,
                        usage.refresh_snapshot, usage.set_background_refresh,
                        usage.snapshot_loaded),
        CsvWarmupTarget('programs', '프로그램 현황', programs.PROGRAM_FILE,
                        programs.refresh_snapshot, programs.set_background_refresh,
                        programs.snapshot_loaded),
    )
