"""Read-only linkage audit. Original CSVs and application behavior are unchanged."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
stats = {}

def norm(value):
    return ' '.join((value or '').split()).casefold()

def read(filename):
    meta = {'rows': 0, 'malformed_rows': 0}
    stats[filename] = meta
    with (DATA / filename).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        meta['headers'] = headers
        for values in reader:
            meta['rows'] += 1
            if len(values) != len(headers):
                meta['malformed_rows'] += 1
                continue
            yield dict(zip(headers, values))

def key(row, detail='DETAIL_ADDR'):
    return tuple(norm(row.get(c)) for c in ['CTPRVN_CD', 'SIGNGU_CD', 'FCLTY_NM', 'FCLTY_ADDR']) + (norm(row.get(detail)),)

facilities = list(read('스포츠강좌이용권 시설 데이터.csv'))
full = defaultdict(list)
base = defaultdict(set)
course_owners = defaultdict(set)
name_address = defaultdict(set)
usage_owners = {}
for i, row in enumerate(facilities):
    k = key(row)
    full[k].append(i)
    base[k[:4]].add(k)
    name_address[(k[2], norm(' '.join([row.get('FCLTY_ADDR', ''), row.get('DETAIL_ADDR', '')])))].add(k)
    if norm(row.get('COURSE_NM')):
        course_owners[(norm(row.get('ITEM_CD')), norm(row.get('COURSE_NM')))].add(k)

result = {'method': 'UTF-8-SIG, permissive csv.reader; malformed-width rows excluded; whitespace collapsed and casefold only; no fuzzy joins.',
          'facility': {'rows': len(facilities), 'identity_keys': len(full),
                       'duplicate_identity_keys': sum(len(v) > 1 for v in full.values()),
                       'ambiguous_base_keys': sum(len(v) > 1 for v in base.values()),
                       'course_fields_populated': {c: sum(bool(norm(r.get(c))) for r in facilities) for c in ['COURSE_NM', 'COURSE_ITEM_NM', 'FCLTY_COURSE_SDIV_NM', 'FCLTY_DECSN_DE']},
                       'distinct_embedded_facility_course_pairs': len({(key(r), norm(r.get('COURSE_NM'))) for r in facilities if norm(r.get('COURSE_NM'))})},
          'sources': {}}

configs = [
 ('스포츠강좌이용권 이용현황 정보.csv', 'FCLTY_DETAIL_ADDR', 'COURSE_NM'),
 ('장애인스포츠강좌이용권 이용현황 정보.csv', 'FCLTY_DETAIL_ADDR', 'COURSE_NM'),
 ('장애인스포츠강좌이용권시설정보.csv', 'FCLTY_DETAIL_ADDR', 'COURSE_NM'),
 ('청소년 유아동 이용가능 체육시설 프로그램 정보.csv', '__none__', 'PROGRM_NM'),
]
for filename, detail, course_col in configs:
    counts = Counter()
    matched_ids = set()
    candidate_ids = set()
    distinct_courses = set()
    periods = Counter()
    fields = Counter()
    code_shapes = Counter()
    month_counts = Counter()
    owners = defaultdict(set)
    address_matches = set()
    address_examples = []
    examples = []
    for row in read(filename):
        k = key(row, detail)
        code_shapes[(len(k[0]), len(k[1]))] += 1
        address_key = (k[2], norm(' '.join([row.get('FCLTY_ADDR', ''), row.get(detail, '')])))
        address_targets = name_address.get(address_key, set())
        if len(address_targets) == 1:
            counts['unique_name_full_address_rows_without_region_code'] += 1
            address_matches.update(address_targets)
            if len(address_examples) < 3 and not any(e['facility'] == row['FCLTY_NM'] for e in address_examples):
                address_examples.append({'facility': row['FCLTY_NM'], 'course': row.get(course_col), 'source_region_codes': list(k[:2]), 'target_region_codes': list(next(iter(address_targets))[:2])})
        if course_col == 'COURSE_NM' and norm(row.get('COURSE_NM')):
            owners[(norm(row.get('ITEM_CD')), norm(row.get('COURSE_NM')))].add(k)
        if row.get('COURSE_ESTBL_YEAR'):
            month_counts[row['COURSE_ESTBL_YEAR'] + '-' + row.get('COURSE_ESTBL_MT', '').zfill(2)] += 1
        targets = set()
        if all(k[:4]):
            if k in full:
                counts['exact_identity_rows'] += 1
                targets = {k}
                matched_ids.add(k)
            elif len(base.get(k[:4], ())) == 1:
                counts['unique_base_but_detail_differs_rows'] += 1
                candidate_ids.update(base[k[:4]])
            elif len(base.get(k[:4], ())) > 1:
                counts['ambiguous_base_rows'] += 1
            else:
                counts['unmatched_rows'] += 1
        else:
            counts['missing_key_rows'] += 1
        if norm(row.get(course_col)):
            counts['course_name_present'] += 1
        period = row.get('COURSE_ESTBL_YEAR') or row.get('PROGRM_BEGIN_DE')
        if period:
            periods[period] += 1
        if targets:
            for c in ['COURSE_NM', 'COURSE_NO', 'COURSE_BEGIN_DE', 'COURSE_END_DE', 'COURSE_PRC', 'PROGRM_NM', 'PROGRM_TRGET_NM', 'PROGRM_ESTBL_WKDAY_NM', 'PROGRM_ESTBL_TIZN_VALUE', 'PROGRM_PRC', 'PROGRM_PRC_TY_NM']:
                if norm(row.get(c)):
                    fields[c] += 1
            if norm(row.get(course_col)):
                distinct_courses.add((k, norm(row.get(course_col))))
                if len(examples) < 3 and not any(e['facility'] == row['FCLTY_NM'] for e in examples):
                    examples.append({'facility': row['FCLTY_NM'], 'course': row[course_col], 'facility_id': 'facility-' + str(full[k][0]), 'year_or_start': period})
    result['sources'][filename] = dict(counts=counts, exact_matched_facility_keys=len(matched_ids),
        exact_matched_current_list_rows=sum(len(full[k]) for k in matched_ids),
        base_candidate_facility_keys=len(candidate_ids), distinct_exact_facility_course_names=len(distinct_courses),
        populated_fields_in_exact_rows=fields, periods=sorted(periods), examples=examples)
    result['sources'][filename]['code_lengths_and_counts'] = {str(k): v for k, v in code_shapes.items()}
    result['sources'][filename]['unique_name_full_address_facility_keys'] = len(address_matches)
    result['sources'][filename]['name_address_examples'] = address_examples
    result['sources'][filename]['latest_year_month_counts'] = dict(sorted(month_counts.items())[-6:])
    usage_owners[filename] = owners

for filename in ['스포츠강좌이용권 이용시설 강좌 데이터.csv', '장애인스포츠강좌이용권 강좌 정보.csv']:
    counts = Counter()
    bridge_owners = usage_owners['장애인스포츠강좌이용권 이용현황 정보.csv' if filename.startswith('장애인') else '스포츠강좌이용권 이용현황 정보.csv']
    variants = defaultdict(set)
    for row in read(filename):
        k = (norm(row.get('ITEM_CD')), norm(row.get('COURSE_NM')))
        variants[k].add(tuple(row.values()))
        n = len(course_owners.get(k, ()))
        counts['no_embedded_owner' if n == 0 else 'one_embedded_owner' if n == 1 else 'multiple_embedded_owners'] += 1
        n_bridge = len(bridge_owners.get(k, ()))
        counts['no_usage_owner' if n_bridge == 0 else 'one_usage_owner' if n_bridge == 1 else 'multiple_usage_owners'] += 1
    result['sources'][filename] = dict(counts=counts, distinct_item_course_keys=len(variants),
         keys_with_multiple_distinct_records=sum(len(v) > 1 for v in variants.values()),
         note='Even one matching owner does not establish a foreign key: these CSVs contain no facility identifier/address.')

result['embedded_course_ownership'] = {'distinct_item_course_keys': len(course_owners),
    'keys_shared_by_multiple_facilities': sum(len(v) > 1 for v in course_owners.values()),
    'examples': [{'course': k[1], 'facility_keys': len(v)} for k, v in sorted(course_owners.items(), key=lambda item: -len(item[1]))[:5]]}
result['files'] = stats
output = ROOT / 'docs' / 'facility-link-audit.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('Audit saved to docs/facility-link-audit.json')
