"""Program search, sorting and summaries shared by page and export."""
from collections import Counter
from . import models
from ..common.data import to_number

def filter_programs(params):
    result = list(models.programs())
    if params.get('region'):
        result = [item for item in result if item['region'] == params['region']]
    if params.get('district'):
        result = [item for item in result if item['district'] == params['district']]
    if params.get('sport'):
        result = [item for item in result if params['sport'].lower() in item['sport'].lower()]
    if params.get('target'):
        result = [item for item in result if params['target'].lower() in item['target'].lower()]
    if params.get('query'):
        query = params['query'].lower()
        result = [item for item in result if query in item['name'].lower() or query in item['facility'].lower()]
    sort_key = params.get('sort', 'name')
    if sort_key == 'fee':
        result.sort(key=lambda item: (to_number(item['fee']) is None, to_number(item['fee']) or 0, item['name'], item['id']))
    else:
        result.sort(key=lambda item: (item['name'], item['id']))
    return result

def program_regions(programs_rows):
    """Distinct regions present in a set of program rows, excluding the 'unknown' placeholder."""
    return sorted({item['region'] for item in programs_rows if item['region'] != '지역 미제공'})

def program_summary(results):
    """Aggregate counts shown on the programs page summary strip."""
    return {
        'region_distribution': Counter(item['region'] for item in results).most_common(),
        'fee_count': sum(1 for item in results if item['fee']),
        'facility_count': len({item['facility'] for item in results if item['facility'] != '시설 연결 미확인'}),
    }
