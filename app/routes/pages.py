from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth import current_user, require_admin
from app.db import get_session
from app.models import Tree, User
from app import moderation

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _ctx(request: Request, user: User | None, **extra) -> dict:
    return {"request": request, "user": user, **extra}


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
):
    return templates.TemplateResponse("index.html", _ctx(request, user))


@router.get("/submit", response_class=HTMLResponse)
def submit(
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
):
    if user is None:
        return RedirectResponse("/auth/login?next=/submit")
    return templates.TemplateResponse("submit.html", _ctx(request, user))


@router.get("/trees/{tree_id}", response_class=HTMLResponse)
def tree_detail(
    tree_id: uuid.UUID,
    request: Request,
    user: Annotated[User | None, Depends(current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    tree = session.get(Tree, tree_id)
    if tree is None or tree.canonical_lat is None:
        raise HTTPException(status_code=404, detail="tree not found")
    return templates.TemplateResponse(
        "tree.html", _ctx(request, user, tree=tree)
    )


@router.get("/admin", response_class=HTMLResponse)
def admin_queue(
    request: Request,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_session)],
):
    pending = moderation.get_pending(session)
    return templates.TemplateResponse(
        "admin.html", _ctx(request, admin, pending=pending)
    )
