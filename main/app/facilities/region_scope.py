"""Feature entry point; shared policy keeps existing names and settings compatible."""
from dataclasses import dataclass

from ..shared.regions import (
    FIXED_MODE, SELECTABLE_MODE, SUPPORTED_MODES, RegionScope, get_region_scope,
)


@dataclass(frozen=True)
class FacilityRegionScope(RegionScope):
    """Facility region selection policy."""


def get_facility_region_scope() -> FacilityRegionScope:
    return get_region_scope('FACILITY_REGION_FILTER_MODE', FacilityRegionScope)
