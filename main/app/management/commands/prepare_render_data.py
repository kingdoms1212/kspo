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


def unpack_sources(archive_path, data_dir, *, overwrite=False):
    """Keep existing nonempty CSVs; stream missing sources to fixed destinations."""
    data_dir = Path(data_dir)
    needed = [spec for spec in SOURCE_SPECS if overwrite
              or not (data_dir / spec.filename).is_file()
              or (data_dir / spec.filename).stat().st_size == 0]
    if not needed:
        return []
    if not Path(archive_path).is_file():
        names = ', '.join(spec.filename for spec in needed)
        raise CommandError(f'원본 CSV({names})와 압축파일이 없습니다: {archive_path}')
    with ZipFile(archive_path) as archive:
        members = {}
        for spec in needed:
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
    return list(members)


class Command(BaseCommand):
    help = 'data/origin.zip을 해제하고 서비스용 지역 CSV를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--force-extract', action='store_true',
                            help='기존 원본 CSV도 ZIP 내용으로 교체합니다.')

    def handle(self, *args, **options):
        data_dir = settings.BASE_DIR.parent / 'data'
        archive = data_dir / 'origin.zip'
        if settings.BATCH_STORAGE_MODE != 'csv':
            raise CommandError('Render CSV 빌드는 BATCH_STORAGE_MODE=csv가 필요합니다.')
        extracted = unpack_sources(archive, data_dir, overwrite=options['force_extract'])
        for spec in SOURCE_SPECS:
            action = '압축 해제 완료' if spec.filename in extracted else '기존 파일 사용 (압축 해제 생략)'
            self.stdout.write(f'{spec.filename}: {action}')
        self.stdout.write('지역 CSV 및 SHA-256 검증 정보 재생성 시작')
        results = refresh_region_data(
            get_region_profile(settings.BATCH_REGION_KEY),
            data_dir=data_dir,
            output_dir=settings.DATA_DIR,
        )
        for result in results:
            self.stdout.write(f'{result.output.name}: {result.matched_rows:,}행')
