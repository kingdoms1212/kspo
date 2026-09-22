from types import SimpleNamespace

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .region_scope import get_facility_region_scope


class FacilityRegionScopeTests(SimpleTestCase):
    @override_settings(FACILITY_REGION_FILTER_MODE="fixed", BATCH_REGION_KEY="seoul")
    def test_fixed_mode_keeps_only_seoul_districts_and_rows(self):
        scope = get_facility_region_scope()
        params = scope.normalize_params({"region": "부산광역시", "district": "강남구"})
        rows = [
            SimpleNamespace(region="서울특별시", district="강남구"),
            SimpleNamespace(region="서울", district="종로구"),
            SimpleNamespace(region="서울특별시", district="고양시"),
            SimpleNamespace(region="경기도", district="고양시"),
        ]

        self.assertFalse(scope.selectable)
        self.assertEqual(params["region"], "")
        self.assertEqual(
            scope.district_options({
                "서울특별시": ["강남구"],
                "서울": ["종로구", "고양시"],
                "경기도": ["고양시"],
            }, ""),
            ["강남구", "종로구"],
        )
        self.assertEqual(
            [(row.region, row.district) for row in scope.filter_rows(rows)],
            [("서울특별시", "강남구"), ("서울", "종로구")],
        )

    @override_settings(FACILITY_REGION_FILTER_MODE="selectable")
    def test_selectable_mode_keeps_selected_region(self):
        scope = get_facility_region_scope()
        params = scope.normalize_params({"region": "서울특별시"})

        self.assertTrue(scope.selectable)
        self.assertEqual(params["region"], "서울특별시")
        self.assertEqual(
            scope.district_options({"서울특별시": ["강남구"]}, "서울특별시"),
            ["강남구"],
        )

    @override_settings(FACILITY_REGION_FILTER_MODE="unknown")
    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "FACILITY_REGION_FILTER_MODE"):
            get_facility_region_scope()
