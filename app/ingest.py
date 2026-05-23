"""Orchestrate one upload: file → EXIF → OCR → DB row."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import ocr, storage
from app.models import Sighting, User


@dataclass
class IngestResult:
    sighting_id: uuid.UUID
    needs_location: bool


def ingest_upload(
    session: Session,
    user: User,
    raw_bytes: bytes,
    content_type: str,
    comment: str | None,
    manual_tag: str | None = None,
) -> IngestResult:
    sighting_id = uuid.uuid4()
    stored = storage.store(sighting_id, raw_bytes, content_type)
    orig_path = stored.orig_path
    thumb_path = stored.thumb_path
    gps = stored.gps

    final_tag = ocr.normalize_tag(manual_tag) if manual_tag else None

    sighting = Sighting(
        id=sighting_id,
        user_id=user.id,
        photo_path=orig_path,
        thumb_path=thumb_path,
        lat=gps[0] if gps else None,
        lon=gps[1] if gps else None,
        gps_source="exif" if gps else "none",
        detected_tag=None,
        detected_conf=None,
        final_tag=final_tag,
        comment=(comment or "").strip() or None,
        status="pending",
    )
    session.add(sighting)
    session.flush()
    return IngestResult(sighting_id=sighting.id, needs_location=gps is None)
