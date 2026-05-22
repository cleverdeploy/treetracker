import io
import uuid

from PIL import Image

from app import storage


def _png_bytes(w=2000, h=1500) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "blue").save(buf, "PNG")
    return buf.getvalue()


def test_store_creates_files_and_thumb():
    sid = uuid.uuid4()
    raw = _png_bytes()
    orig, thumb = storage.store(sid, raw, "image/png")
    assert orig.endswith(".png")
    assert thumb.endswith(".jpg")

    o = Image.open(orig)
    assert o.size == (2000, 1500)
    t = Image.open(thumb)
    assert max(t.size) <= storage.THUMB_MAX
