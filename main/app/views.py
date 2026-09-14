"""Compatibility imports; app.urls routes directly to feature controllers."""
from .dashboard.views import dashboard
from .programs.views import programs, export_programs
from .facilities.views import facilities, export_facilities, export_facility_transit
from .policies.views import policies
