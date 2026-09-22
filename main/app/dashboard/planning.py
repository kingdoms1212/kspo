"""Transient program plans. No database, session or filesystem persistence."""
from django import forms
from django.core import signing

from ..facilities import models as facilities
from .services import dashboard_data, selected_districts

REGIONS = (
    ('서울', '서울특별시'), ('부산', '부산광역시'), ('대구', '대구광역시'),
    ('인천', '인천광역시'), ('광주', '광주광역시'), ('대전', '대전광역시'),
    ('울산', '울산광역시'), ('세종', '세종특별자치시'), ('경기', '경기도'),
    ('강원', '강원도', '강원특별자치도'), ('충북', '충청북도'), ('충남', '충청남도'),
    ('전북', '전라북도', '전북특별자치도'), ('전남', '전라남도'),
    ('경북', '경상북도'), ('경남', '경상남도'), ('제주', '제주도', '제주특별자치도'),
)
# Only explicit sport/type evidence qualifies; a generic gym is not inferred
# to support basketball, nor does a historical application imply availability.
SPORT_TYPES = {
    '농구': ('농구', '농구장'), '수영': ('수영', '수영장', '수영장업'),
    '태권도': ('태권도', '태권도장'), '축구': ('축구', '축구장'),
    '풋살': ('풋살', '풋살장'), '배드민턴': ('배드민턴', '배드민턴장'),
    '탁구': ('탁구', '탁구장', '탁구장업'), '테니스': ('테니스', '테니스장'),
    '골프': ('골프', '골프장', '골프연습장', '골프연습장업', '골프장업'),
    '헬스': ('헬스', '체력단련장', '체력단련장업'),
    '복싱': ('복싱', '권투', '권투장'), '유도': ('유도', '유도장'),
    '합기도': ('합기도', '합기도장'), '검도': ('검도', '검도장'),
    '야구': ('야구', '야구장'), '볼링': ('볼링', '볼링장', '볼링장업'),
}


def region_key(value):
    return next((names[0] for names in REGIONS if value in names), value)


def candidates(region, district, sport):
    districts = selected_districts(district)
    types = SPORT_TYPES.get(sport, ())
    if not region or not types:
        return []
    return [row for row in facilities.facilities()
            if region_key(row.region) == region_key(region)
            and (not districts or row.district in districts)
            and row.state == facilities.OPERATING
            and (row.facility_type in types or row.industry in types)]


def facility_token(row):
    # Repository IDs depend on row order. Bind selection to its displayed
    # identity as well, so a changed source cannot silently choose another site.
    return signing.dumps([row.id, row.name, row.address], salt='program-plan')


class ScopeForm(forms.Form):
    region = forms.CharField(max_length=30)
    district = forms.CharField(required=False, max_length=300)
    sport = forms.ChoiceField(choices=[(name, name) for name in SPORT_TYPES])

    def clean(self):
        cleaned = super().clean()
        region = cleaned.get('region', '')
        district = cleaned.get('district', '')
        self.statistics = dashboard_data(region, district)
        if region not in self.statistics['region_options']:
            self.add_error('region', '지도에서 조회할 시·도를 선택해 주세요.')
        elif any(name not in self.statistics['region_district_options'].get(region, [])
                 for name in selected_districts(district)):
            self.add_error('district', '선택 지역에 속하는 시·군·구를 다시 선택해 주세요.')
        return cleaned


class PlanForm(ScopeForm):
    ai_review = forms.BooleanField(required=False)
    without_facility = forms.BooleanField(required=False)
    target = forms.CharField(required=False, max_length=100)
    start = forms.DateField(required=False)
    end = forms.DateField(required=False)
    name = forms.CharField(max_length=100)
    capacity = forms.IntegerField(min_value=1, max_value=100000)
    description = forms.CharField(max_length=2000)
    fee = forms.IntegerField(min_value=0, max_value=100000000)
    fee_unit = forms.ChoiceField(choices=[('월', '월'), ('회', '회'), ('과정', '과정')])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('start') and cleaned.get('end') and cleaned['start'] > cleaned['end']:
            self.add_error('end', '종료일은 시작일보다 빠를 수 없습니다.')
        tokens = self.data.getlist('facilities')
        if (not tokens and not cleaned.get('without_facility')) or len(tokens) > 20 or len(tokens) != len(set(tokens)):
            self.add_error(None, '시설은 중복 없이 1~20곳 선택해 주세요.')
            return cleaned
        if any(field not in cleaned for field in ('region', 'sport', 'district')):
            return cleaned
        eligible = {row.id: row for row in candidates(cleaned['region'], cleaned['district'], cleaned['sport'])}
        self.selected = []
        # [SH260917] 동의와 실제 후보 부재를 모두 검증하여 시설 미정 계획을 허용합니다.
        if not tokens:
            if eligible:
                self.add_error(None, '매칭되는 후보 시설이 있습니다. 시설을 선택해 주세요.')
            return cleaned
        try:
            for token in tokens:
                identity = signing.loads(token, salt='program-plan', max_age=7200)
                row = eligible.get(identity[0])
                if row is None or identity != [row.id, row.name, row.address]:
                    raise ValueError('Facility identity changed')
                self.selected.append(row)
        except (signing.BadSignature, ValueError, TypeError, IndexError):
            self.add_error(None, '지역·종목·시설 자료가 변경되었거나 선택이 만료되었습니다. 시설을 다시 선택해 주세요.')
        return cleaned
