"""Photo file storage on a mounted volume."""

from __future__ import annotations

import io
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import pillow_heif
from PIL import ExifTags, Image

from app.config import get_settings

pillow_heif.register_heif_opener()

THUMB_MAX = 1200
_GPS_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "GPSInfo")


@dataclass
class StoredPhoto:
    orig_path: str
    thumb_path: str
    gps: tuple[float, float] | None  # extracted from EXIF before re-encoding


def _root() -> Path:
    root = Path(get_settings().photos_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _to_degrees(value) -> float:
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def _gps_from_exif(exif: dict) -> tuple[float, float] | None:
    if not exif or _GPS_TAG not in exif:
        return None
    gps_raw = exif[_GPS_TAG]
    if not hasattr(gps_raw, "items"):
        return None  # newer Pillow may return an int offset here
    gps = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_raw.items()}
    try:
        lat = _to_degrees(gps["GPSLatitude"])
        lon = _to_degrees(gps["GPSLongitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if str(gps.get("GPSLatitudeRef", "N")).upper() == "S":
        lat = -lat
    if str(gps.get("GPSLongitudeRef", "E")).upper() == "W":
        lon = -lon
    return lat, lon


def store(sighting_id: uuid.UUID, raw_bytes: bytes, content_type: str) -> StoredPhoto:
    """Write original (converting HEIC→JPEG) + 1200px thumb. Extracts GPS from the
    incoming EXIF *before* re-encoding (Pillow strips EXIF by default on save)."""
    dest = _root() / str(sighting_id)
    dest.mkdir(parents=True, exist_ok=True)

    img = Image.open(io.BytesIO(raw_bytes))
    img.load()

    exif_bytes = img.info.get("exif")
    try:
        legacy_exif = img._getexif() or {}  # nested dicts: {GPSInfo: {GPSLatitude: ...}}
    except Exception:
        legacy_exif = {}
    gps = _gps_from_exif(legacy_exif)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    ext = "jpg" if content_type in ("image/jpeg", "image/heic") else content_type.split("/")[-1]
    if ext not in ("jpg", "png"):
        ext = "jpg"
    orig_path = dest / f"original.{ext}"
    save_kwargs: dict = {"quality": 92}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    img.save(orig_path, "JPEG" if ext == "jpg" else "PNG", **save_kwargs)

    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX, THUMB_MAX))
    if thumb.mode != "RGB":
        thumb = thumb.convert("RGB")
    thumb_path = dest / "thumb.jpg"
    thumb.save(thumb_path, "JPEG", quality=85)

    return StoredPhoto(orig_path=str(orig_path), thumb_path=str(thumb_path), gps=gps)


def delete(sighting_id: uuid.UUID) -> None:
    """Remove a sighting's photo directory. No-op if it doesn't exist."""
    root = _root().resolve()
    dest = (root / str(sighting_id)).resolve()
    if not dest.is_relative_to(root):
        raise ValueError("refusing to delete outside photos_dir")
    shutil.rmtree(dest, ignore_errors=True)
