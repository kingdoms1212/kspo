"""Compatibility imports; business logic lives in feature modules."""
from .dashboard.services import dashboard_data, region_chart_rows
from .programs.services import filter_programs, program_regions, program_summary
from .facilities.services import filter_facilities
from .common.calculations import benefit_rate, calculate_budget, nearest_stop_minutes
