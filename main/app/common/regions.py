"""CSV 정제와 지도에서 공유할 지역 프로필을 관리한다."""
from dataclasses import dataclass


def _compact(value: str) -> str:
    """지역명의 공백 차이를 제거해 비교한다."""
    return "".join(str(value or "").split())


@dataclass(frozen=True)
class RegionProfile:
    """원본 CSV 필터와 출력 파일명에 필요한 지역 설정이다."""

    key: str
    display_name: str
    output_suffix: str
    source_code_prefixes: frozenset[str]
    source_name_aliases: frozenset[str]
    district_names: frozenset[str] = frozenset()
    map_code: str | None = None
    include_all: bool = False

    def __post_init__(self):
        # 별칭은 프로필 생성 시 한 번만 정규화해 대용량 CSV 비교 비용을 줄인다.
        object.__setattr__(
            self,
            "source_name_aliases",
            frozenset(_compact(alias) for alias in self.source_name_aliases),
        )
        object.__setattr__(
            self,
            "district_names",
            frozenset(_compact(name) for name in self.district_names),
        )

    def matches(self, code: str, name: str) -> bool:
        """구조화된 시도 코드를 우선해 현재 지역 포함 여부를 판단한다."""
        if self.include_all:
            return True

        normalized_code = str(code or "").strip()
        if normalized_code:
            if any(normalized_code.startswith(prefix)
                   for prefix in self.source_code_prefixes):
                return True
            # 유효한 타 지역 코드는 이름보다 우선한다.
            if normalized_code.isdigit():
                return False

        normalized_name = _compact(name)
        return normalized_name in self.source_name_aliases

    def matches_district(self, name: str) -> bool:
        """현재 지역에 속한 시군구인지 확인한다."""
        return self.include_all or _compact(name) in self.district_names


REGION_PROFILES = {
    "seoul": RegionProfile(
        key="seoul",
        display_name="서울",
        output_suffix="seoul",
        source_code_prefixes=frozenset({"11"}),
        source_name_aliases=frozenset({"서울", "서울시", "서울특별시"}),
        # 서울로 잘못 표기된 타 지역 행이 화면에 섞이지 않도록 25개 자치구를 검증한다.
        district_names=frozenset({
            "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구",
            "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구",
            "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구",
            "은평구", "종로구", "중구", "중랑구",
        }),
        map_code="11",
    ),
    "national": RegionProfile(
        key="national",
        display_name="전국",
        output_suffix="national",
        source_code_prefixes=frozenset(),
        source_name_aliases=frozenset(),
        include_all=True,
    ),
}


def get_region_profile(key: str) -> RegionProfile:
    """설정 키에 해당하는 지역 프로필을 반환한다."""
    try:
        return REGION_PROFILES[key]
    except KeyError as error:
        choices = ", ".join(sorted(REGION_PROFILES))
        raise ValueError(f"지원하지 않는 지역 프로필입니다: {key}, 선택값={choices}") from error
