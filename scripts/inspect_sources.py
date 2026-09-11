"""Inventory supplied CSVs without logging records or personal fields."""
import csv
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    inventory = []
    for path in sorted((root / 'data').glob('*.csv')):
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        item = {'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
        for encoding in ('utf-8-sig', 'cp949'):
            try:
                with path.open(encoding=encoding, newline='') as source:
                    reader = csv.reader(source, strict=True)
                    headers = next(reader)
                    count = malformed = 0
                    try:
                        for row in reader:
                            count += 1
                            malformed += len(row) != len(headers)
                    except csv.Error as error:
                        item['strict_csv_error'] = str(error)
                        item['strict_error_line'] = reader.line_num
                # Reproduce the existing loader's permissive dialect, while keeping
                # the strict error visible. This does not certify the source.
                if 'strict_csv_error' in item:
                    count = malformed = 0
                    with path.open(encoding=encoding, newline='') as source:
                        reader = csv.reader(source)
                        next(reader)
                        for row in reader:
                            count += 1
                            malformed += len(row) != len(headers)
                item.update(encoding=encoding, headers=headers, row_count=count,
                            column_count_mismatch=malformed)
                break
            except UnicodeDecodeError:
                continue
        else:
            item['error'] = 'Encoding requires inspection'
        inventory.append(item)
    destination = root / 'docs' / 'source-inventory.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Inspected {len(inventory)} CSVs; metadata saved to docs/source-inventory.json')


if __name__ == '__main__':
    main()
