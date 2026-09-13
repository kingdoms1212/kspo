"""Shared CSV decoding and scalar normalization; no feature rules."""
import csv
from pathlib import Path
from django.conf import settings

def clean(value):
    return (value or '').strip()

def to_number(value):
    try:
        return int(float(value)) if value else None
    except (TypeError, ValueError):
        return None

def _read_rows(filename, limit=None):
    path = Path(settings.DATA_DIR) / filename
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        rows = []
        for row in reader:
            rows.append({key: clean(value) for key, value in row.items()})
            if limit and len(rows) >= limit:
                break
        return rows
