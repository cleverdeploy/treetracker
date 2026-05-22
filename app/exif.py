"""Extract GPS coordinates from image EXIF."""

from __future__ import annotations

from PIL import ExifTags, Image

_GPS_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "GPSInfo")


def _to_degrees(value) -> float:
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_gps(path: str) -> tuple[float, float] | None:
    try:
        img = Image.open(path)
        exif = img._getexif()  # type: ignore[attr-defined]
    except Exception:
        return None
    if not exif or _GPS_TAG not in exif:
        return None

    gps_raw = exif[_GPS_TAG]
    gps: dict[str, object] = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

    try:
        lat = _to_degrees(gps["GPSLatitude"])  # type: ignore[arg-type]
        lon = _to_degrees(gps["GPSLongitude"])  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError):
        return None

    if str(gps.get("GPSLatitudeRef", "N")).upper() == "S":
        lat = -lat
    if str(gps.get("GPSLongitudeRef", "E")).upper() == "W":
        lon = -lon
    return lat, lon
