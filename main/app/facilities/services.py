"""Facility search shared by page and export."""

def filter_facilities(rows, region='', query=''):
    """Apply the region/text filters shared by the facilities page and its Excel export."""
    if region:
        rows = [row for row in rows if row['region'] == region]
    if query:
        query = query.lower()
        rows = [row for row in rows if query in row['name'].lower() or query in row['address'].lower()]
    return rows
