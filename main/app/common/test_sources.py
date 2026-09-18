"""원본 이름이 한 곳에서만 정해지는지 확인한다."""
from django.test import SimpleTestCase

from . import sources
from ..Batch import seoul_csv_batch
from ..dashboard import models as dashboard
from ..facilities import models as facilities
from ..facilities import transit
from ..programs import models as programs


class SourceRegistryTests(SimpleTestCase):
    def test_every_repository_reads_the_name_the_registry_defines(self):
        for constant, spec in ((programs.PROGRAM_FILE, sources.PROGRAM),
                               (dashboard.USAGE_FILE, sources.USAGE),
                               (facilities.FACILITY_FILE, sources.FACILITY),
                               (transit.TRANSIT_FILE, sources.TRANSIT)):
            with self.subTest(spec=spec.filename):
                self.assertEqual(constant, spec.final_filename)

    def test_the_batch_writes_exactly_the_four_files_the_screens_read(self):
        # 같은 객체를 공유해야 배치 출력과 화면 입력 경로가 어긋나지 않는다.
        self.assertIs(seoul_csv_batch.SOURCE_SPECS, sources.SOURCE_SPECS)
        self.assertEqual({spec.final_filename for spec in seoul_csv_batch.SOURCE_SPECS},
                         {programs.PROGRAM_FILE, dashboard.USAGE_FILE,
                          facilities.FACILITY_FILE, transit.TRANSIT_FILE})

    def test_derived_names_follow_the_batch_naming_rule_and_stay_distinct(self):
        for spec in sources.SOURCE_SPECS:
            with self.subTest(spec=spec.filename):
                stem = spec.filename.removesuffix('.csv')
                self.assertEqual(spec.final_filename, stem + '_seoul.csv')
        names = [spec.final_filename for spec in sources.SOURCE_SPECS]
        self.assertEqual(len(set(names)), 4)
