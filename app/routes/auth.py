from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import oauth, upsert_user_from_google
from app.config import get_settings
from app.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request, next: str = "/"):
    request.session["post_login_redirect"] = next
    redirect_uri = get_settings().oauth_redirect_url
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request, session: Annotated[Session, Depends(get_session)]):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"oauth failure: {e}")
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    user = upsert_user_from_google(session, dict(userinfo))
    request.session["user_id"] = str(user.id)
    nxt = request.session.pop("post_login_redirect", "/")
    return RedirectResponse(nxt)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
