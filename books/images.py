"""Image processing helpers for book uploads.

Every uploaded photo is verified, auto-rotated, downscaled and re-encoded as
WebP so a 5 MB phone photo becomes a ~150 KB file. This keeps pages fast and
storage cheap without touching the templates.
"""
import io
import os

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

# Hard limits
MAX_UPLOAD_BYTES = 8 * 1024 * 1024      # reject anything above 8 MB
MAX_DIMENSION = 1400                    # longest edge after resizing
THUMB_DIMENSION = 420                   # small card thumbnail
WEBP_QUALITY = 82
THUMB_QUALITY = 78


def _to_webp(image, quality=WEBP_QUALITY):
    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=quality, method=4)
    buffer.seek(0)
    return buffer


def optimize_upload(uploaded_file, max_dimension=MAX_DIMENSION, quality=WEBP_QUALITY):
    """Validate and compress an uploaded image.

    Returns a ``ContentFile`` (WebP) ready to assign to an ImageField, or
    ``None`` when no file was given. Raises ``ValidationError`` for files that
    are too large or are not real images.
    """
    if not uploaded_file:
        return None

    if getattr(uploaded_file, 'size', 0) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f'Photo is too large ({uploaded_file.size / 1024 / 1024:.1f} MB). '
            'Please use a photo smaller than 8 MB.'
        )

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.verify()                 # detects corrupt / non-image files
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
    except ValidationError:
        raise
    except Exception:
        raise ValidationError('That file could not be read as an image.')

    # Flatten transparency / palette modes onto white for a clean WebP.
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        converted = image.convert('RGBA')
        background.paste(converted, mask=converted.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = _to_webp(image, quality)
    return ContentFile(buffer.getvalue(), name=_webp_name(uploaded_file.name))


def make_thumbnail(source_file, dimension=THUMB_DIMENSION):
    """Create a small square-ish thumbnail ``ContentFile`` from a stored image."""
    if not source_file:
        return None
    try:
        source_file.open('rb')
        image = Image.open(source_file)
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.thumbnail((dimension, dimension), Image.LANCZOS)
        buffer = _to_webp(image, THUMB_QUALITY)
        name = _thumb_name(getattr(source_file, 'name', 'thumb.jpg'))
        return ContentFile(buffer.getvalue(), name=name)
    except Exception:
        return None
    finally:
        try:
            source_file.close()
        except Exception:
            pass


def _webp_name(original_name):
    base = os.path.splitext(os.path.basename(original_name or 'book'))[0]
    base = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in base)[:60] or 'book'
    return f'{base}.webp'


def _thumb_name(name):
    base, _ = os.path.splitext(os.path.basename(name))
    return f'{base}_thumb.webp'


def save_optimized_image(instance, field_name='image'):
    """Compress an already-assigned ImageField value in place.

    Used after a model has been saved with a raw upload so the stored file is
    the WebP version. Returns True when the file was replaced.
    """
    field = getattr(instance, field_name)
    if not field or not field.name:
        return False

    storage = field.storage
    try:
        with storage.open(field.name, 'rb') as handle:
            raw = handle.read()
    except Exception:
        return False

    # Already optimised by us — nothing to do.
    if field.name.lower().endswith('.webp'):
        return False

    from django.core.files.base import ContentFile
    import io as _io

    try:
        image = Image.open(_io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        if max(image.size) > MAX_DIMENSION:
            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        buffer = _to_webp(image)
        new_name = _webp_name(field.name)
        old_name = field.name
        field.save(new_name, ContentFile(buffer.getvalue()), save=False)
        instance.save(update_fields=[field_name])
        try:
            if old_name and old_name != field.name:
                storage.delete(old_name)
        except Exception:
            pass
        return True
    except Exception:
        return False
