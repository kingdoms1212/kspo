"""프로그램 검색의 고정 지역과 전국 선택 모드를 분리한다."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


FIXED_MODE = "fixed"
SELECTABLE_MODE = "selectable"
SUPPORTED_MODES = {FIXED_MODE, SELECTABLE_MODE}


@dataclass(frozen=True)
class ProgramRegionScope:
    """지역 검색 UI와 요청값 처리 규칙을 한곳에서 관리한다."""

    mode: str

    @property
    def selectable(self) -> bool:
        return self.mode == SELECTABLE_MODE

    def normalize_params(self, params: dict) -> dict:
        """고정 지역 모드에서는 외부의 region 요청값을 검색에 사용하지 않는다."""
        normalized = dict(params)
        if not self.selectable:
            normalized["region"] = ""
        return normalized

    def district_options(self, region_district_map: dict, selected_region: str) -> list[str]:
        """현재 모드에서 선택할 수 있는 시군구 목록을 반환한다."""
        if self.selectable:
            return list(region_district_map.get(selected_region, ())) if selected_region else []
        return sorted({
            district
            for districts in region_district_map.values()
            for district in districts
        })


def get_program_region_scope() -> ProgramRegionScope:
    """설정값을 검증해 프로그램 지역 검색 모드를 만든다."""
    mode = str(
        getattr(settings, "PROGRAM_REGION_FILTER_MODE", FIXED_MODE)
    ).strip().lower()
    if mode not in SUPPORTED_MODES:
        choices = ", ".join(sorted(SUPPORTED_MODES))
        raise ImproperlyConfigured(
            f"PROGRAM_REGION_FILTER_MODE은 {choices} 중 하나여야 합니다: {mode}"
        )
    return ProgramRegionScope(mode)
