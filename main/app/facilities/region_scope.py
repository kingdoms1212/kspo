"""시설 현황의 지역 선택 범위를 관리한다."""
from dataclasses import dataclass

from django.conf import settings

from ..common.regions import get_region_profile
from ..shared.regions import (
    FIXED_MODE, SELECTABLE_MODE, SUPPORTED_MODES, RegionScope, get_region_scope,
)


@dataclass(frozen=True)
class FacilityRegionScope(RegionScope):
    """시설 현황의 고정 지역과 전국 선택 모드를 분리한다."""

    def _fixed_profile(self):
        """현재 배치 대상 지역의 공통 표기 규칙을 반환한다."""
        return get_region_profile(settings.BATCH_REGION_KEY)

    def includes_region(self, region: str) -> bool:
        """고정 모드에서는 현재 배치 대상 지역만 허용한다."""
        return self.selectable or self._fixed_profile().matches('', region)

    def includes_district(self, district: str) -> bool:
        """고정 모드에서는 현재 배치 대상 지역의 시군구만 허용한다."""
        return self.selectable or self._fixed_profile().matches_district(district)

    def filter_rows(self, rows):
        """목록과 내보내기에 사용할 시설을 현재 지역으로 제한한다."""
        if self.selectable:
            return rows
        return [
            row for row in rows
            if self.includes_region(row.region)
            and self.includes_district(row.district)
        ]

    def district_options(self, region_district_map: dict,
                         selected_region: str) -> list[str]:
        """고정 모드에서는 서울 별칭에 속한 구만 노출한다."""
        if self.selectable:
            return super().district_options(region_district_map, selected_region)
        return sorted({
            district
            for region, districts in region_district_map.items()
            if self.includes_region(region)
            for district in districts
            if self.includes_district(district)
        })


def get_facility_region_scope() -> FacilityRegionScope:
    return get_region_scope('FACILITY_REGION_FILTER_MODE', FacilityRegionScope)
