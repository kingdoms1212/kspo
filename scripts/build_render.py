"""Render build command; execute from any working directory."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for arguments in (
        ['-m', 'pip', 'install', '-r', 'main/requirements.txt'],
        ['main/manage.py', 'check'],
        ['main/manage.py', 'prepare_render_data'],
        ['main/manage.py', 'collectstatic', '--noinput'],
    ):
        subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
