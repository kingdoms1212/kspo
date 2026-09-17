"""시설 검색의 고정 지역과 전국 선택 모드를 분리한다."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


FIXED_MODE = "fixed"
SELECTABLE_MODE = "selectable"
SUPPORTED_MODES = {FIXED_MODE, SELECTABLE_MODE}


@dataclass(frozen=True)
class FacilityRegionScope:
    """시설 지역 검색 UI와 요청값 처리 규칙을 관리한다."""

    mode: str

    @property
    def selectable(self) -> bool:
        return self.mode == SELECTABLE_MODE

    def normalize_params(self, params: dict) -> dict:
        """서울 고정 모드에서는 외부 region 요청값을 검색에 사용하지 않는다."""
        normalized = dict(params)
        if not self.selectable:
            normalized["region"] = ""
        return normalized

    def district_options(self, region_district_map: dict, selected_region: str) -> list[str]:
        """현재 모드에서 선택 가능한 시군구 목록을 반환한다."""
        if self.selectable:
            return list(region_district_map.get(selected_region, ())) if selected_region else []
        return sorted({
            district
            for districts in region_district_map.values()
            for district in districts
        })


def get_facility_region_scope() -> FacilityRegionScope:
    """설정값을 검증해 시설 지역 검색 모드를 만든다."""
    mode = str(
        getattr(settings, "FACILITY_REGION_FILTER_MODE", FIXED_MODE)
    ).strip().lower()
    if mode not in SUPPORTED_MODES:
        choices = ", ".join(sorted(SUPPORTED_MODES))
        raise ImproperlyConfigured(
            f"FACILITY_REGION_FILTER_MODE은 {choices} 중 하나여야 합니다: {mode}"
        )
    return FacilityRegionScope(mode)
