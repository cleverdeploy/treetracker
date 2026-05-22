"""Serve sighting photos through FastAPI so we can add auth checks later."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Sighting

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{sighting_id}/thumb")
def thumb(sighting_id: uuid.UUID, session: Annotated[Session, Depends(get_session)]):
    return _serve(session, sighting_id, "thumb")


@router.get("/{sighting_id}/full")
def full(sighting_id: uuid.UUID, session: Annotated[Session, Depends(get_session)]):
    return _serve(session, sighting_id, "full")


def _serve(session: Session, sighting_id: uuid.UUID, kind: str):
    s = session.get(Sighting, sighting_id)
    if s is None:
        raise HTTPException(status_code=404, detail="not found")
    path = Path(s.thumb_path if kind == "thumb" else s.photo_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(path)
