"""Pure calculations shared across features."""

def benefit_rate(target_count, beneficiary_count):
    """Return a ratio only when both counts are known and the denominator is valid."""
    if target_count is None or beneficiary_count is None or target_count <= 0:
        return None
    return beneficiary_count / target_count

def nearest_stop_minutes(walking_seconds):
    """Return the minimum observed facility-to-stop walk time, preserving missing data."""
    valid = [value for value in walking_seconds if value is not None and value >= 0]
    return min(valid) / 60 if valid else None

def calculate_budget(budget, planned_people, months, fee):
    """Calculate a monthly, per-person fee scenario without inferring other fee units."""
    if budget is None:
        return {'status': 'not_requested', 'cost': None, 'supported_people': None}
    if planned_people is None or planned_people < 1 or months is None or months < 1:
        return {'status': 'invalid_plan', 'cost': None, 'supported_people': None}
    if fee is None or fee < 0:
        return {'status': 'unverified_fee', 'cost': None, 'supported_people': None}
    cost = fee * planned_people * months
    supported = None if fee == 0 else budget // (fee * months)
    return {
        'status': 'within_budget' if cost <= budget else 'over_budget',
        'cost': cost,
        'supported_people': supported,
    }
