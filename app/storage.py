"""Photo file storage on a mounted volume."""

from __future__ import annotations

import uuid
from pathlib import Path

import pillow_heif
from PIL import Image

from app.config import get_settings

pillow_heif.register_heif_opener()

THUMB_MAX = 1200


def _root() -> Path:
    root = Path(get_settings().photos_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def store(sighting_id: uuid.UUID, raw_bytes: bytes, content_type: str) -> tuple[str, str]:
    """Write the original file (converting HEIC→JPEG) and a 1200px thumb. Returns (orig_path, thumb_path)."""
    dest = _root() / str(sighting_id)
    dest.mkdir(parents=True, exist_ok=True)

    tmp = dest / "incoming.bin"
    tmp.write_bytes(raw_bytes)
    img = Image.open(tmp)
    img.load()
    tmp.unlink(missing_ok=True)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    ext = "jpg" if content_type in ("image/jpeg", "image/heic") else (content_type.split("/")[-1])
    if ext not in ("jpg", "png"):
        ext = "jpg"
    orig_path = dest / f"original.{ext}"
    save_format = "JPEG" if ext == "jpg" else "PNG"
    img.save(orig_path, save_format, quality=92)

    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX, THUMB_MAX))
    thumb_path = dest / "thumb.jpg"
    if thumb.mode != "RGB":
        thumb = thumb.convert("RGB")
    thumb.save(thumb_path, "JPEG", quality=85)

    return str(orig_path), str(thumb_path)
