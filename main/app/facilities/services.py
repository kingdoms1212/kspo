"""Facility search and transport linking shared by page and export."""
from functools import lru_cache

from . import models, transit


def filter_facilities(rows, region='', industry='', flag='', state='', owner='', query=''):
    """Apply the filters shared by the facilities page and its Excel export."""
    if region:
        rows = [row for row in rows if row.region == region]
    if industry:
        rows = [row for row in rows if row.industry == industry]
    if flag:
        rows = [row for row in rows if row.flag == flag]
    if state:
        rows = [row for row in rows if row.state == state]
    if owner:
        rows = [row for row in rows if row.owner == owner]
    if query:
        query = query.lower()
        rows = [row for row in rows if query in row.name.lower() or query in row.address.lower()]
    return rows


def facility_regions(rows):
    return sorted({row.region for row in rows if row.region != '지역 미제공'})


def facility_industries(rows):
    return sorted({row.industry for row in rows if row.industry != '업종 미제공'})


def facility_flags(rows):
    """Register categories: public facilities against filed private ones."""
    return sorted({row.flag for row in rows if row.flag != '구분 미제공'})


def facility_states(rows):
    """Operating states the register records, closed ones included."""
    return sorted({row.state for row in rows if row.state != '운영상태 미제공'})


def facility_owners(rows):
    """Owning bodies present in the register.

    Most public facilities belong to a local authority and private ones record
    no owner at all, so this filter earns its place the other way round: it is
    how the handful held by a national body can be found.
    """
    return sorted({row.owner for row in rows if row.owner != '보유주체 미제공'})


@lru_cache(maxsize=1)
def _positions():
    """Facility positions the register holds, so the transit index skips the rest."""
    return frozenset(row.geo_key for row in models.facilities() if row.geo_key)


def facility_transit(facility):
    """Nearby stops for this exact site, or the reason none are shown.

    The link is geometric -- name plus position -- because the two registers
    write addresses in different systems and a name repeats within a district.
    """
    if facility is None:
        return None
    return transit.stops_for(facility, _positions())


def cache_clear():
    _positions.cache_clear()
    transit.cache_clear()
