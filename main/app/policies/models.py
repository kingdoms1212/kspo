"""Cached access to the external policy listing.

The dialog opens often and the source is a public site, so a successful read is
held for a while. A failure is held only briefly, so a site that comes back up
is picked up on the next open rather than after the full window.
"""
import time

from django.conf import settings
from django.utils import timezone

from ..common import crawler

_cache = {'at': None, 'result': None}


def _source():
    return settings.POLICY_SOURCE


def policies(force=False):
    """Latest policies, the reason none are shown, and when they were read."""
    source = _source()
    now = time.monotonic()
    cached = _cache['result']
    if not force and cached is not None:
        window = source['retry_seconds'] if cached['error'] else source['cache_seconds']
        if now - _cache['at'] < window:
            return cached
    items, error = crawler.crawl(source)
    result = {
        'policies': items,
        'error': error,
        'source': source['name'],
        'source_url': crawler.list_url(source),
        'fetched_at': timezone.localtime(),
    }
    _cache.update(at=now, result=result)
    return result


def cache_clear():
    _cache.update(at=None, result=None)
