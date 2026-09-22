"""Chart presentation helpers; no repository reads or request handling."""
from math import cos, sin, pi


def chart_sort(value):
    return value if value in ('asc', 'desc') else 'desc'


def normalized_chart_rows(rows, order='desc'):
    """Copy and sort all rows; express counts on the current min/max interval.

    Missing values sort last in either direction and have no bar. A constant
    positive series uses full bars; an all-zero series uses zero-width marks.
    Normalization uses every row, independently of sort and viewport position.
    """
    rows = list(rows)
    values = [row['requests'] for row in rows if row.get('requests') is not None]
    minimum, maximum = (min(values), max(values)) if values else (None, None)
    result = []
    for row in rows:
        value = row.get('requests')
        if value is None:
            width = None
        elif minimum == maximum:
            width = 100.0 if value > 0 else 0.0
        else:
            width = round((value - minimum) / (maximum - minimum) * 100, 6)
        result.append({**row, 'bar_percent': width})
    direction = 1 if chart_sort(order) == 'asc' else -1
    return sorted(result, key=lambda row: (
        row.get('requests') is None,
        direction * (row.get('requests') or 0),
        row.get('name', ''), row.get('region', ''), row.get('district', ''),
    ))


def region_chart_rows(areas, order='desc'):
    return normalized_chart_rows(areas, order)


#: Shared column layout for every pie-chart legend table (`dashboard/_pie.html`).
#: Region and sport tables reuse the same template, so only the label for the
#: "name" column (지역 vs 종목) actually differs between callers; every other
#: column is identical. Keeping the full list here — instead of hardcoding
#: `<th>` text in the template — means a future column only needs an entry
#: here plus one matching cell in the template, and no caller can silently
#: drift out of sync with what the template renders.
PIE_TABLE_COLUMNS = (
    {'key': 'color', 'label': '색상'},
    {'key': 'rank', 'label': '순위'},
    {'key': 'name', 'label': None},  # label filled in per call via name_label
    {'key': 'facilities', 'label': '시설 수'},
    {'key': 'courses', 'label': '강좌 수'},
    {'key': 'requests', 'label': '신청인원'},
    {'key': 'share', 'label': '비율'},
)


def pie_table_columns(name_label):
    """Column headers for a pie legend table, with the row-identity column labelled
    for this table's actual identity (예: 지역, 종목)."""
    return [
        {**column, 'label': name_label} if column['key'] == 'name' else column
        for column in PIE_TABLE_COLUMNS
    ]


def pie_chart_data(rows, name_label='지역'):
    """Pie angles use actual positive counts, independently of bar normalization.

    `name_label` names whatever the rows are grouped by (지역, 종목, ...) — it only
    drives the legend table's column header, never row identity or sort order.
    """
    rows = list(rows)
    canonical = sorted(rows, key=lambda row: (-(row.get('requests') or 0), row.get('name', ''), row.get('region', ''), row.get('district', '')))
    total = sum(max(row.get('requests') or 0, 0) for row in rows)
    palette = ('--si-map-5', '--si-map-3', '--si-chart-primary', '--si-map-2', '--si-navy')
    segments, legend = [], []
    cumulative = 0
    for index, row in enumerate(canonical):
        value = max(row.get('requests') or 0, 0)
        start = cumulative / total * 100 if total else 0
        cumulative += value
        end = cumulative / total * 100 if total else 0
        color = palette[index % len(palette)]
        if value and total:
            segments.append(f'var({color}) {start:.8f}% {end:.8f}%')
        start_angle, end_angle = start / 100 * 2 * pi - pi / 2, end / 100 * 2 * pi - pi / 2
        path = (f'M 100 100 L {100 + 95 * cos(start_angle):.6f} {100 + 95 * sin(start_angle):.6f} '
                f'A 95 95 0 {int(end - start > 50)} 1 '
                f'{100 + 95 * cos(end_angle):.6f} {100 + 95 * sin(end_angle):.6f} Z')
        legend.append({**row, 'number': index + 1, 'color': color, 'path': path,
                       'share': value / total * 100 if total else 0})
    by_identity = {id(row): item for row, item in zip(canonical, legend)}
    return {'rows': [by_identity[id(row)] for row in rows], 'total': total,
            'gradient': 'conic-gradient(' + ', '.join(segments) + ')' if segments else 'none',
            'columns': pie_table_columns(name_label)}


