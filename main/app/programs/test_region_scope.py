from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .region_scope import get_program_region_scope


class ProgramRegionScopeTests(SimpleTestCase):
    @override_settings(PROGRAM_REGION_FILTER_MODE="fixed")
    def test_fixed_mode_ignores_region_and_combines_districts(self):
        scope = get_program_region_scope()

        params = scope.normalize_params({"region": "부산광역시", "district": "강남구"})

        self.assertFalse(scope.selectable)
        self.assertEqual(params["region"], "")
        self.assertEqual(
            scope.district_options({"서울특별시": ["강남구"], "서울": ["종로구"]}, ""),
            ["강남구", "종로구"],
        )

    @override_settings(PROGRAM_REGION_FILTER_MODE="selectable")
    def test_selectable_mode_keeps_region_and_its_districts(self):
        scope = get_program_region_scope()

        params = scope.normalize_params({"region": "서울특별시"})

        self.assertTrue(scope.selectable)
        self.assertEqual(params["region"], "서울특별시")
        self.assertEqual(
            scope.district_options({"서울특별시": ["강남구"]}, "서울특별시"),
            ["강남구"],
        )

    @override_settings(PROGRAM_REGION_FILTER_MODE="unknown")
    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "PROGRAM_REGION_FILTER_MODE"):
            get_program_region_scope()
