from unittest import TestCase

from .regions import get_region_profile


class RegionProfileTests(TestCase):
    def test_seoul_accepts_code_and_name_aliases(self):
        profile = get_region_profile("seoul")

        self.assertTrue(profile.matches("11", ""))
        self.assertTrue(profile.matches("", "서울시"))
        self.assertTrue(profile.matches("", " 서울 특별시 "))

    def test_valid_other_region_code_has_priority_over_name(self):
        profile = get_region_profile("seoul")

        self.assertFalse(profile.matches("26", "서울특별시"))

    def test_national_profile_accepts_missing_region(self):
        profile = get_region_profile("national")

        self.assertTrue(profile.matches("", ""))
