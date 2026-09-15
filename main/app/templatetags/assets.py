"""Static URLs stamped with the file's own modification time.

A hand-typed cache-busting token only works while someone remembers to change
it. Editing a stylesheet without bumping the token leaves every returning
browser on the previous copy, so a new rule looks like it was never written.
The stamp comes from the file, so it cannot drift from the content.
"""
import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    """The static URL for `path` with a `?v=` stamp taken from the file."""
    url = static(path)
    located = finders.find(path)
    if isinstance(located, (list, tuple)):
        located = located[0] if located else None
    try:
        return f'{url}?v={int(os.path.getmtime(located))}'
    except (TypeError, OSError):
        # Collected or missing files still get a working URL, just unstamped.
        return url


CENTRE_PHOTOS = 10


@register.simple_tag
def centre_photo(identifier):
    """A stand-in facility photo chosen by the trailing digit of an id.

    The register carries no photograph, so ten interchangeable images stand in.
    Picking by the id's last digit keeps one facility on one image between
    visits, instead of shuffling every render.
    """
    digits = [character for character in str(identifier) if character.isdigit()]
    index = int(digits[-1]) if digits else 0
    return static(f'image/center/center{index % CENTRE_PHOTOS}.jpg')
