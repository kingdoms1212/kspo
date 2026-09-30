# 서정길 [SJG011] 운영 설정 — 배포·진단 및 월간 배치 일정
"""Initialize Django's database, then replace this process with Gunicorn."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    subprocess.run([sys.executable, 'main/manage.py', 'migrate', '--noinput'], check=True)
    os.execv(sys.executable, [sys.executable, '-m', 'gunicorn',
                            '--config', 'gunicorn.conf.py', 'main.wsgi:application'])


if __name__ == '__main__':
    main()
