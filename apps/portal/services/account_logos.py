"""Compact raster logos, preserving aspect ratio and alpha."""

from io import BytesIO

from PIL import Image, ImageOps


def compact_logo(source):
    """Keep the smaller of optimized PNG and high-quality WebP."""
    image = ImageOps.exif_transpose(source).convert("RGBA")
    image.thumbnail((384, 384), Image.Resampling.LANCZOS)
    candidates = []
    for options in (
        {"format": "WEBP", "quality": 90, "method": 6},
        {"format": "PNG", "optimize": True},
    ):
        output = BytesIO()
        image.save(output, **options)
        candidates.append(output.getvalue())
    return min(candidates, key=len)


def content_type(data):
    """Stored legacy PNG logos remain readable without a migration."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"
