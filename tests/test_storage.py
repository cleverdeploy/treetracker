import io
import uuid
from pathlib import Path

import piexif
from PIL import Image

from app import exif as exif_mod
from app import storage


def _png_bytes(w=2000, h=1500) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "blue").save(buf, "PNG")
    return buf.getvalue()


def test_store_creates_files_and_thumb():
    sid = uuid.uuid4()
    raw = _png_bytes()
    stored = storage.store(sid, raw, "image/png")
    assert stored.orig_path.endswith(".png")
    assert stored.thumb_path.endswith(".jpg")
    assert stored.gps is None  # no EXIF on plain PNG

    o = Image.open(stored.orig_path)
    assert o.size == (2000, 1500)
    t = Image.open(stored.thumb_path)
    assert max(t.size) <= storage.THUMB_MAX


def test_delete_removes_photo_dir():
    sid = uuid.uuid4()
    stored = storage.store(sid, _png_bytes(), "image/png")
    photo_dir = Path(stored.orig_path).parent
    assert photo_dir.is_dir()
    storage.delete(sid)
    assert not photo_dir.exists()
    storage.delete(sid)  # second call is a no-op, not an error


def _jpeg_with_gps_bytes() -> bytes:
    img = Image.new("RGB", (1200, 900), "green")
    exif_dict = {
        "0th": {}, "Exif": {}, "1st": {}, "thumbnail": None,
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((52, 1), (11, 1), (3000, 100)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((1, 1), (42, 1), (2880, 100)),
        },
    }
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=piexif.dump(exif_dict))
    return buf.getvalue()


def test_store_extracts_gps_and_preserves_exif():
    """The bug: Pillow's save() strips EXIF by default, so GPS was lost before extraction."""
    sid = uuid.uuid4()
    raw = _jpeg_with_gps_bytes()
    stored = storage.store(sid, raw, "image/jpeg")
    # GPS extracted from the in-memory image (before re-encoding)
    assert stored.gps is not None
    lat, lon = stored.gps
    assert 52.18 < lat < 52.20
    assert -1.72 < lon < -1.70
    # And re-extracting from the saved file also works (EXIF preserved on disk)
    assert exif_mod.extract_gps(stored.orig_path) is not None
