"""Serve one view as either a full page or the fragment htmx asked for.

Every screen keeps a single controller and a single context. The shell template
renders the chrome plus the fragment; an htmx request renders the fragment
alone, so the browser replaces one region and leaves scroll position, focus and
the rest of the document untouched.
"""
from django.shortcuts import render


def is_history_restore(request):
    """True when the browser went back or forward.

    htmx restores history by re-requesting the URL, and that request still
    carries HX-Request. It then swaps the answer into the history element --
    the whole body -- so a fragment would leave the page with no chrome. A
    restore must be answered with the full page.
    """
    return request.headers.get('HX-History-Restore-Request') == 'true'


def is_htmx(request):
    """True when htmx is swapping one region, not navigating the whole page."""
    return request.headers.get('HX-Request') == 'true' and not is_history_restore(request)


def render_screen(request, page_template, fragment_template, context):
    """Full page on navigation or history restore, fragment on an htmx swap.

    `htmx_fragment` lets a shared fragment emit out-of-band updates only when
    it is the whole response; the full page renders those regions in place.
    """
    fragment = is_htmx(request)
    return render(request, fragment_template if fragment else page_template,
                  {**context, 'htmx_fragment': fragment})
