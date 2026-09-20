from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from app.facilities.region_scope import FacilityRegionScope, get_facility_region_scope
from app.programs.region_scope import ProgramRegionScope, get_program_region_scope
from .regions import region_district_map


class SharedRegionTests(SimpleTestCase):
    @override_settings(PROGRAM_REGION_FILTER_MODE=' SELECTABLE ', FACILITY_REGION_FILTER_MODE='fixed')
    def test_shared_policy_keeps_feature_settings_and_types_independent(self):
        program, facility = get_program_region_scope(), get_facility_region_scope()
        original = {'region': '부산', 'district': '중구', 'query': '수영'}
        self.assertIsInstance(program, ProgramRegionScope)
        self.assertIsInstance(facility, FacilityRegionScope)
        self.assertEqual(program.normalize_params(original), original)
        self.assertEqual(facility.normalize_params(original), {**original, 'region': ''})
        self.assertEqual(original['region'], '부산')

    def test_options_drop_only_missing_regions_and_deduplicate_without_mutating_rows(self):
        pairs = [('서울', '중구'), ('서울', '강남구'), ('서울', '중구'),
                 ('부산', '중구'), ('지역 미제공', '중구'), ('서울', '시군구 미제공'),
                 ('', '중구'), ('서울', '')]
        rows = [SimpleNamespace(region=region, district=district) for region, district in pairs]
        self.assertEqual(region_district_map(rows), {'부산': ['중구'], '서울': ['강남구', '중구']})
        self.assertEqual([(row.region, row.district) for row in rows], pairs)
