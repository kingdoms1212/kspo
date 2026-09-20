"""One worker owns the in-process weekly scheduler and CSV caches."""
import os
from pathlib import Path

chdir = str(Path(__file__).resolve().parent / 'main')
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
worker_class = 'gthread'
threads = 4
timeout = 180
accesslog = '-'
errorlog = '-'
capture_output = True
preload_app = False


def post_worker_init(worker):
    from django.conf import settings
    if settings.BATCH_SCHEDULER_ENABLED:
        from app.Batch.scheduler import start_scheduler
        start_scheduler()


def worker_exit(server, worker):
    from app.common.csv_warmup import stop_csv_warmup
    stop_csv_warmup()
    from app.Batch.scheduler import stop_scheduler
    stop_scheduler()
