"""Compatibility entry points. Web process lifecycle lives in app.runtime."""
from ..runtime.csv_warmup import start_csv_warmup, stop_csv_warmup, warm_csv_caches

__all__ = ['start_csv_warmup', 'stop_csv_warmup', 'warm_csv_caches']
