from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import ingest as ingest_mod
from app import moderation, ratelimit
from app.auth import current_user, require_admin, require_user
from app.db import get_session
from app.models import Sighting, Tree, User

router = APIRouter(prefix="/api", tags=["api"])

ALLOWED_MIME = {"image/jpeg", "image/png", "image/heic", "image/heif"}
MAX_BYTES = 15 * 1024 * 1024


class LocationPatch(BaseModel):
    lat: float
    lon: float


class ApprovePayload(BaseModel):
    final_tag: str
    lat: float | None = None
    lon: float | None = None


class RejectPayload(BaseModel):
    reason: str


@router.post("/sightings", status_code=201)
async def create_sighting(
    user: Annotated[User, Depends(require_user)],
    session: Annotated[Session, Depends(get_session)],
    photo: UploadFile = File(...),
    comment: str | None = Form(None),
    manual_tag: str | None = Form(None),
):
    if not ratelimit.check(user.id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    if photo.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"unsupported type: {photo.content_type}")
    raw = await photo.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large (15 MB max)")
    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")

    result = ingest_mod.ingest_upload(
        session,
        user=user,
        raw_bytes=raw,
        content_type=photo.content_type or "image/jpeg",
        comment=comment,
        manual_tag=manual_tag,
    )
    return {"id": str(result.sighting_id), "needs_location": result.needs_location}


@router.patch("/sightings/{sighting_id}/location")
def patch_location(
    sighting_id: uuid.UUID,
    payload: LocationPatch,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[Session, Depends(get_session)],
):
    s = session.get(Sighting, sighting_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    if s.status != "pending":
        raise HTTPException(status_code=409, detail="already reviewed")
    s.lat = payload.lat
    s.lon = payload.lon
    s.gps_source = "manual"
    return {"ok": True}


@router.get("/trees.geojson")
def trees_geojson(session: Annotated[Session, Depends(get_session)]):
    rows = session.scalars(
        select(Tree).where(Tree.canonical_lat.is_not(None)).order_by(Tree.tag_number)
    ).all()
    features = []
    for t in rows:
        thumb = session.scalar(
            select(Sighting.id)
            .where(Sighting.tree_id == t.id, Sighting.status == "approved")
            .order_by(Sighting.created_at.desc())
            .limit(1)
        )
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [t.canonical_lon, t.canonical_lat],
                },
                "properties": {
                    "id": str(t.id),
                    "tag_number": t.tag_number,
                    "sighting_count": t.sighting_count,
                    "thumb_url": f"/photos/{thumb}/thumb" if thumb else None,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/trees/{tree_id}")
def get_tree(tree_id: uuid.UUID, session: Annotated[Session, Depends(get_session)]):
    tree = session.get(Tree, tree_id)
    if tree is None or tree.canonical_lat is None:
        raise HTTPException(status_code=404, detail="not found")
    sightings = session.scalars(
        select(Sighting)
        .where(Sighting.tree_id == tree.id, Sighting.status == "approved")
        .order_by(Sighting.created_at.desc())
    ).all()
    return {
        "id": str(tree.id),
        "tag_number": tree.tag_number,
        "lat": tree.canonical_lat,
        "lon": tree.canonical_lon,
        "first_seen_at": tree.first_seen_at.isoformat(),
        "last_seen_at": tree.last_seen_at.isoformat(),
        "sightings": [
            {
                "id": str(s.id),
                "thumb_url": f"/photos/{s.id}/thumb",
                "photo_url": f"/photos/{s.id}/full",
                "comment": s.comment,
                "submitter": s.user.name or s.user.email,
                "created_at": s.created_at.isoformat(),
            }
            for s in sightings
        ],
    }


@router.post("/sightings/{sighting_id}/approve")
def approve_sighting(
    sighting_id: uuid.UUID,
    payload: ApprovePayload,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
):
    s = session.get(Sighting, sighting_id)
    if s is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        tree = moderation.approve(session, s, admin, payload.final_tag, payload.lat, payload.lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "tree_id": str(tree.id)}


@router.post("/sightings/{sighting_id}/reject")
def reject_sighting(
    sighting_id: uuid.UUID,
    payload: RejectPayload,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
):
    s = session.get(Sighting, sighting_id)
    if s is None:
        raise HTTPException(status_code=404, detail="not found")
    moderation.reject(session, s, admin, payload.reason)
    return {"ok": True}
