from pathlib import Path
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from app.common.regions import get_region_profile

from . import data_refresh


class RegionDataRefreshTests(SimpleTestCase):
    def setUp(self):
        self.profile = get_region_profile("seoul")

    @override_settings(BATCH_STORAGE_MODE="csv")
    @patch.object(data_refresh, "refresh_region_csvs", return_value=["csv-result"])
    def test_csv_mode_uses_existing_csv_batch(self, refresh_csvs):
        result = data_refresh.refresh_region_data(
            self.profile,
            data_dir=Path("source"),
            output_dir=Path("output"),
            specs=(),
        )

        self.assertEqual(result, ["csv-result"])
        refresh_csvs.assert_called_once()

    @override_settings(BATCH_STORAGE_MODE="db", BATCH_DB_WRITER="tests.writer")
    @patch.object(data_refresh, "import_string")
    def test_db_mode_uses_configured_writer(self, import_string):
        writer = Mock(return_value=["db-result"])
        import_string.return_value = writer

        result = data_refresh.refresh_region_data(
            self.profile,
            data_dir=Path("source"),
            output_dir=Path("output"),
            specs=(),
        )

        self.assertEqual(result, ["db-result"])
        import_string.assert_called_once_with("tests.writer")
        writer.assert_called_once()

    @override_settings(BATCH_STORAGE_MODE="db", BATCH_DB_WRITER="")
    def test_db_mode_requires_writer(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "BATCH_DB_WRITER"):
            data_refresh.refresh_region_data(self.profile, specs=())

    @override_settings(BATCH_STORAGE_MODE="unknown")
    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "BATCH_STORAGE_MODE"):
            data_refresh.refresh_region_data(self.profile, specs=())
