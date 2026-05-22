"""Google OAuth sign-in and session helpers."""

from __future__ import annotations

import uuid
from typing import Annotated

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import User

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def configure_oauth() -> None:
    s = get_settings()
    oauth.google.client_id = s.google_client_id  # type: ignore[union-attr]
    oauth.google.client_secret = s.google_client_secret  # type: ignore[union-attr]


def upsert_user_from_google(session: Session, userinfo: dict) -> User:
    sub = userinfo["sub"]
    email = userinfo["email"]
    user = session.scalar(select(User).where(User.google_sub == sub))
    settings = get_settings()
    if user is None:
        user = User(
            google_sub=sub,
            email=email,
            name=userinfo.get("name"),
            picture_url=userinfo.get("picture"),
            is_admin=email.lower() in settings.admin_email_set,
        )
        session.add(user)
        session.flush()
    else:
        user.email = email
        user.name = userinfo.get("name") or user.name
        user.picture_url = userinfo.get("picture") or user.picture_url
        if email.lower() in settings.admin_email_set and not user.is_admin:
            user.is_admin = True
    return user


def current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    try:
        return session.get(User, uuid.UUID(uid))
    except (ValueError, TypeError):
        return None


def require_user(user: Annotated[User | None, Depends(current_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
    return user


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
