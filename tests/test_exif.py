import piexif
from PIL import Image

from app.exif import extract_gps


def _write_jpeg(path, with_gps=True):
    img = Image.new("RGB", (32, 32), "green")
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    if with_gps:
        # Stratford-upon-Avon, ~52.1917, -1.7080
        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((52, 1), (11, 1), (3000, 100)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((1, 1), (42, 1), (2880, 100)),
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, "JPEG", exif=exif_bytes)
    else:
        img.save(path, "JPEG")


def test_extract_gps_present(tmp_path):
    pytest_importorskip = __import__("pytest").importorskip
    pytest_importorskip("piexif")
    p = tmp_path / "with_gps.jpg"
    _write_jpeg(p, with_gps=True)
    result = extract_gps(str(p))
    assert result is not None
    lat, lon = result
    assert 52.18 < lat < 52.20
    assert -1.72 < lon < -1.70


def test_extract_gps_absent(tmp_path):
    p = tmp_path / "no_gps.jpg"
    _write_jpeg(p, with_gps=False)
    assert extract_gps(str(p)) is None


def test_extract_gps_not_image(tmp_path):
    p = tmp_path / "not.jpg"
    p.write_bytes(b"hello")
    assert extract_gps(str(p)) is None
