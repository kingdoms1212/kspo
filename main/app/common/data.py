"""Shared CSV decoding and scalar normalization; no feature rules."""
import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from django.conf import settings

def clean(value):
    return (value or '').strip()

def to_number(value):
    try:
        return int(float(value)) if value else None
    except (TypeError, ValueError):
        return None

@lru_cache(maxsize=4096)
def course_month(year, month):
    """Return YYYY-MM only for a fully valid year/month pair, else 'unknown'.

    Memoised: the usage ledger repeats a few hundred year/month pairs across
    half a million rows.
    """
    if year.isascii() and year.isdigit() and len(year) == 4 and month.isascii() and month.isdigit():
        if 1 <= int(year) <= 9999 and 1 <= int(month) <= 12:
            return f'{year}-{int(month):02d}'
    return 'unknown'

@lru_cache(maxsize=16384)
def iso_date(value):
    """Normalize a source date to YYYY-MM-DD, preserving unrecognised text as-is.

    Memoised for the same reason as course_month; strptime is the slowest step
    in reading the ledger.
    """
    for fmt in ('%Y%m%d', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return value or '미제공'

def normalize(value):
    """Collapse whitespace and case so two spellings of one code or name match."""
    return ' '.join((value or '').split()).casefold()


def facility_key(ctprvn_cd, signgu_cd, name, address):
    """Shared facility identity: administrative codes plus name and road address.

    Returns None unless every part is present, so a partial record is reported
    as unlinked instead of being joined on a facility name alone.
    """
    key = (normalize(ctprvn_cd), normalize(signgu_cd), normalize(name), normalize(address))
    return key if all(key) else None


def strip_markup(value):
    """Source text carries literal <br> tags; keep the words, drop the tag."""
    text = value.replace('<br/>', ' ').replace('<br />', ' ').replace('<br>', ' ')
    return ' '.join(text.split())


def data_path(filename):
    return Path(settings.DATA_DIR) / filename

def _read_rows(filename, limit=None):
    path = data_path(filename)
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

def columns_present(filename, columns):
    """[SG001] - 시설 현황 데이터 예외처리 보완
    자료 파일에 기대한 열이 모두 있는지 확인한다.

    `read_columns`는 열이 없으면 아무 행도 내보내지 않고 조용히 끝난다. 그
    상태는 '이 시설에 자료가 없다'와 구분되지 않아, 원본 열 이름이 바뀌면 모든
    시설이 '정보 없음'으로 보인다. 읽기 전에 따로 확인해 두 경우를 가른다.
    """
    path = data_path(filename)
    if not path.exists():
        return False
    try:
        with path.open('r', encoding='utf-8-sig', newline='') as source:
            headers = next(csv.reader(source), [])
    except (OSError, UnicodeError, csv.Error):
        return False
    return set(columns).issubset(headers)


def read_columns(filename, columns):
    """Stream only the requested columns, skipping rows whose width is wrong.

    Values are interned so the large usage ledger shares its repeated region,
    facility and sport strings instead of holding one object per row.
    """
    path = data_path(filename)
    if not path.exists():
        return
    pool = {}
    with path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source)
        headers = next(reader, [])
        if not set(columns).issubset(headers):
            return
        index = [headers.index(column) for column in columns]
        width = len(headers)
        for values in reader:
            if len(values) != width:
                continue
            yield tuple(pool.setdefault(v, v) for v in (values[i].strip() for i in index))
