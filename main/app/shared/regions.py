"""프로그램·시설 화면에서 공유하는 지역 선택 정책."""
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

FIXED_MODE = 'fixed'
SELECTABLE_MODE = 'selectable'
SUPPORTED_MODES = {FIXED_MODE, SELECTABLE_MODE}


@dataclass(frozen=True)
class RegionScope:
    mode: str

    @property
    def selectable(self) -> bool:
        return self.mode == SELECTABLE_MODE

    def normalize_params(self, params: dict) -> dict:
        normalized = dict(params)
        if not self.selectable:
            normalized['region'] = ''
        return normalized

    def district_options(self, region_district_map: dict, selected_region: str) -> list[str]:
        if self.selectable:
            return list(region_district_map.get(selected_region, ())) if selected_region else []
        return sorted({district for districts in region_district_map.values() for district in districts})


def get_region_scope(setting_name: str, scope_type=RegionScope) -> RegionScope:
    """검증은 공유하되 각 화면의 설정 이름과 반환 타입은 유지한다."""
    mode = str(getattr(settings, setting_name, FIXED_MODE)).strip().lower()
    if mode not in SUPPORTED_MODES:
        choices = ', '.join(sorted(SUPPORTED_MODES))
        raise ImproperlyConfigured(f'{setting_name}은 {choices} 중 하나여야 합니다: {mode}')
    return scope_type(mode)


def region_district_map(rows):
    """명시된 지역·시군구를 정렬한다. 집계와 업무별 필터는 호출부에서 처리한다."""
    districts_by_region = {}
    for row in rows:
        region, district = row.region, row.district
        if not region or not district or region == '지역 미제공' or district == '시군구 미제공':
            continue
        districts_by_region.setdefault(region, set()).add(district)
    return {region: sorted(districts) for region, districts in sorted(districts_by_region.items())}
