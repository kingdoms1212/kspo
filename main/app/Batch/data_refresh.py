"""설정에 따라 지역 데이터의 반영 대상을 선택한다."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from app.common.regions import RegionProfile

from .regional_csv_batch import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT_DIR,
    SOURCE_SPECS,
    SourceSpec,
    refresh_region_csvs,
)


CSV_MODE = "csv"
DB_MODE = "db"
SUPPORTED_STORAGE_MODES = {CSV_MODE, DB_MODE}


def get_storage_mode() -> str:
    """설정된 데이터 반영 방식을 검증해 반환한다."""
    mode = str(getattr(settings, "BATCH_STORAGE_MODE", CSV_MODE)).strip().lower()
    if mode not in SUPPORTED_STORAGE_MODES:
        choices = ", ".join(sorted(SUPPORTED_STORAGE_MODES))
        raise ImproperlyConfigured(
            f"BATCH_STORAGE_MODE은 {choices} 중 하나여야 합니다: {mode}"
        )
    return mode


def _load_db_writer() -> Callable:
    """추후 구현할 DB 저장기를 Django import 경로로 불러온다."""
    writer_path = str(getattr(settings, "BATCH_DB_WRITER", "")).strip()
    if not writer_path:
        raise ImproperlyConfigured(
            "DB 방식에는 BATCH_DB_WRITER 설정이 필요합니다. "
            "DB 모델과 저장기가 준비될 때까지 BATCH_STORAGE_MODE을 csv로 유지하세요."
        )
    writer = import_string(writer_path)
    if not callable(writer):
        raise ImproperlyConfigured("BATCH_DB_WRITER는 호출 가능한 함수여야 합니다.")
    return writer


def refresh_region_data(
    profile: RegionProfile,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    specs: tuple[SourceSpec, ...] = SOURCE_SPECS,
    progress_callback: Callable[[int, str], None] | None = None,
):
    """정제 규칙은 유지하고 설정에 맞는 저장 방식으로 지역 데이터를 반영한다.

    CSV 방식은 현재의 안전한 파일 교체 로직을 사용한다. DB 방식은 추후 DB
    모델이 확정되면 ``BATCH_DB_WRITER``에 등록한 저장기로 같은 인자를 전달한다.
    따라서 예약 실행과 수동 실행 코드는 저장 방식이 바뀌어도 수정하지 않는다.
    """
    common_options = {
        "data_dir": Path(data_dir),
        "output_dir": Path(output_dir),
        "specs": specs,
        "progress_callback": progress_callback,
    }
    if get_storage_mode() == CSV_MODE:
        return refresh_region_csvs(profile, **common_options)

    # DB 스키마가 확정되면 저장기만 구현해 이 확장 지점에 연결한다.
    return _load_db_writer()(profile=profile, **common_options)
