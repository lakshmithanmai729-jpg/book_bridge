"""Template helpers for BookBridge."""
import os

from django import template
from django.core.files.storage import default_storage

from books.images import make_thumbnail

register = template.Library()


@register.filter
def thumb(image_field, size=400):
    """Return a cached thumbnail URL for an ImageField, generated on first use.

    Falls back to the original image URL whenever anything goes wrong, so the
    template never breaks because of a missing file or storage hiccup.
    """
    if not image_field:
        return ''

    try:
        name = image_field.name
    except Exception:
        return ''

    if not name:
        return ''

    try:
        dimension = int(size)
    except (TypeError, ValueError):
        dimension = 400

    base, _ = os.path.splitext(name)
    thumb_name = f'thumbs/{base}_{dimension}.webp'

    try:
        if default_storage.exists(thumb_name):
            return default_storage.url(thumb_name)

        content = make_thumbnail(image_field, dimension)
        if content is None:
            return image_field.url

        saved_name = default_storage.save(thumb_name, content)
        return default_storage.url(saved_name)
    except Exception:
        try:
            return image_field.url
        except Exception:
            return ''


@register.filter
def price_label(value):
    """Show a clean rupee amount: 250.00 → ₹250, 249.50 → ₹249.50"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return f'₹{value}'
    if amount == int(amount):
        return f'₹{int(amount):,}'
    return f'₹{amount:,.2f}'
