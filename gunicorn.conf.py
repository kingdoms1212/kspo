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


def on_starting(server):
    server.log.info('CSV_DIAG gunicorn.start pid=%s preload=%s workers=%s threads=%s',
                    os.getpid(), server.cfg.preload_app, server.cfg.workers, server.cfg.threads)


def post_fork(server, worker):
    server.log.info('CSV_DIAG worker.fork pid=%s parent=%s', os.getpid(), os.getppid())


def post_worker_init(worker):
    worker.log.info('CSV_DIAG worker.init pid=%s parent=%s', os.getpid(), os.getppid())
    from django.conf import settings
    if settings.BATCH_SCHEDULER_ENABLED:
        from app.Batch.scheduler import start_scheduler
        start_scheduler()
    worker.log.info('CSV_DIAG worker.init.end pid=%s', os.getpid())


def worker_exit(server, worker):
    from app.runtime.csv_warmup import stop_csv_warmup
    stop_csv_warmup()
    from app.Batch.scheduler import stop_scheduler
    stop_scheduler()
