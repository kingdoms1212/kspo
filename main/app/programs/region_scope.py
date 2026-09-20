"""Feature entry point; shared policy keeps existing names and settings compatible."""
from dataclasses import dataclass

from ..shared.regions import (
    FIXED_MODE, SELECTABLE_MODE, SUPPORTED_MODES, RegionScope, get_region_scope,
)


@dataclass(frozen=True)
class ProgramRegionScope(RegionScope):
    """Program region selection policy."""


def get_program_region_scope() -> ProgramRegionScope:
    return get_region_scope('PROGRAM_REGION_FILTER_MODE', ProgramRegionScope)
