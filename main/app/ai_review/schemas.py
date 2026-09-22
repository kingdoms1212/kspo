CRITERIA = {
    'population_fit': '인구·대상 적합성', 'sports_demand': '종목 수요',
    'facility_supply': '시설 공급', 'facility_fit': '시설 적합성',
    'transport_accessibility': '대중교통 접근성', 'welfare_need': '체육복지 필요성',
    'budget_feasibility': '예산·규모 적정성',
}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
TEXT_LIST = {'type': 'array', 'items': TEXT, 'maxItems': 8}
EVALUATION = {'type': 'object', 'properties': {
    'score': {'type': ['integer', 'null'], 'minimum': 0, 'maximum': 100},
    'reason': TEXT, 'evidence_keys': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 8},
}, 'required': ['score', 'reason', 'evidence_keys'], 'additionalProperties': False}
RESPONSE_SCHEMA = {'type': 'object', 'properties': {
    'summary': TEXT,
    'evaluations': {'type': 'object', 'properties': {key: EVALUATION for key in CRITERIA},
                    'required': list(CRITERIA), 'additionalProperties': False},
    **{key: TEXT_LIST for key in ('strengths', 'risks', 'recommendations', 'limitations')},
}, 'required': ['summary', 'evaluations', 'strengths', 'risks', 'recommendations', 'limitations'],
    'additionalProperties': False}


def response_schema(evidence):
    keys = [key for key in CRITERIA if evidence['available_criteria'].get(key)]
    return {**RESPONSE_SCHEMA, 'properties': {**RESPONSE_SCHEMA['properties'],
        'evaluations': {'type': 'object', 'properties': {key: EVALUATION for key in keys},
                        'required': keys, 'additionalProperties': False}}}


def normalize_analysis(data, evidence):
    def text(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError('invalid_text')
        return value
    if not isinstance(data, dict) or set(data) != set(RESPONSE_SCHEMA['required']):
        raise ValueError('invalid_fields')
    evaluations = data['evaluations']
    if not isinstance(evaluations, dict) or set(evaluations) != set(evidence['available_criteria']):
        raise ValueError('invalid_criteria')
    result = {'summary': text(data['summary']), 'findings': []}
    scores = []
    for key, title in CRITERIA.items():
        if key not in evidence['available_criteria']:
            continue
        item = evaluations[key]
        if not isinstance(item, dict) or set(item) != {'score', 'reason', 'evidence_keys'}:
            raise ValueError('invalid_evaluation')
        # [SG003] AI기능 연동 시 예외처리 보완 — 미채점 항목도 설명 형식을 검증합니다.
        reason = text(item['reason'])
        score, refs = item['score'], item['evidence_keys']
        if score is not None and (type(score) is not int or not 0 <= score <= 100):
            raise ValueError('invalid_score')
        allowed = evidence['available_criteria'][key]
        if not isinstance(refs, list) or len(refs) > 8 or any(not isinstance(r, str) or r not in allowed for r in refs):
            raise ValueError('invalid_evidence')
        if score is not None and (not allowed or not refs):
            raise ValueError('unsupported_score')
        if score is not None:
            scores.append(score)
        if score is None:
            continue
        result['findings'].append({'title': title, 'score': score,
            'status': '판단 자료 부족' if score is None else f'{score}점',
            'comment': reason, 'evidence_keys': refs})
    for key in ('strengths', 'risks', 'recommendations', 'limitations'):
        values = data[key]
        if not isinstance(values, list) or len(values) > 8:
            raise ValueError('invalid_list')
        result['suggestions' if key == 'recommendations' else key] = [text(v) for v in values]
    overall = int(sum(scores) / len(scores) + .5) if scores else None
    result.update(overall_score=overall, scored_count=len(scores), criterion_count=len(evidence['available_criteria']),
        grade=('판단 자료 부족' if overall is None else '매우 적합' if overall >= 80 else
               '적합' if overall >= 60 else '검토 필요' if overall >= 40 else '부적합'))
    return result
