"""Unpack the committed source archive and build the configured regional CSVs."""
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app.Batch.data_refresh import refresh_region_data
from app.Batch.regional_csv_batch import SOURCE_SPECS
from app.common.regions import get_region_profile


def unpack_sources(archive_path, data_dir):
    """Stream only known members to fixed destinations; never extract arbitrary paths."""
    data_dir = Path(data_dir)
    with ZipFile(archive_path) as archive:
        members = {}
        for spec in SOURCE_SPECS:
            matches = [item for item in archive.infolist()
                       if item.filename in (spec.filename, f'origin/{spec.filename}')]
            if len(matches) != 1 or matches[0].file_size == 0:
                raise CommandError(f'압축파일의 원본 CSV가 없거나 중복/빈 파일입니다: {spec.filename}')
            members[spec.filename] = matches[0]
        data_dir.mkdir(parents=True, exist_ok=True)
        for filename, member in members.items():
            target = data_dir / filename
            part = target.with_suffix('.csv.unpack.part')
            try:
                with archive.open(member) as source, part.open('wb') as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                os.replace(part, target)
            finally:
                part.unlink(missing_ok=True)


class Command(BaseCommand):
    help = 'data/origin.zip을 해제하고 서비스용 지역 CSV를 생성합니다.'

    def handle(self, *args, **options):
        data_dir = settings.BASE_DIR.parent / 'data'
        archive = data_dir / 'origin.zip'
        if not archive.is_file():
            raise CommandError(f'배포에 필요한 압축파일이 없습니다: {archive}')
        if settings.BATCH_STORAGE_MODE != 'csv':
            raise CommandError('Render CSV 빌드는 BATCH_STORAGE_MODE=csv가 필요합니다.')
        self.stdout.write(f'원본 압축 해제: {archive}', ending='\n')
        unpack_sources(archive, data_dir)
        results = refresh_region_data(
            get_region_profile(settings.BATCH_REGION_KEY),
            data_dir=data_dir,
            output_dir=settings.DATA_DIR,
        )
        for result in results:
            self.stdout.write(f'{result.output.name}: {result.matched_rows:,}행')
