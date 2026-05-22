"""Approve/reject sightings; find-or-create trees; recompute aggregates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import ocr
from app.models import AuditLog, Sighting, Tree, User


def approve(
    session: Session,
    sighting: Sighting,
    admin: User,
    final_tag: str,
    lat: float | None = None,
    lon: float | None = None,
) -> Tree:
    tag = ocr.normalize_tag(final_tag)
    if not tag:
        raise ValueError("final_tag must contain digits")

    if lat is not None:
        sighting.lat = lat
        sighting.lon = lon
        sighting.gps_source = "manual"
    if sighting.lat is None or sighting.lon is None:
        raise ValueError("sighting has no location")

    now = datetime.now(timezone.utc)
    tree = session.scalar(select(Tree).where(Tree.tag_number == tag))
    if tree is None:
        tree = Tree(
            tag_number=tag,
            first_seen_at=now,
            last_seen_at=now,
            sighting_count=0,
        )
        session.add(tree)
        session.flush()

    sighting.tree_id = tree.id
    sighting.final_tag = tag
    sighting.status = "approved"
    sighting.reviewed_at = now
    sighting.reviewed_by = admin.id
    session.flush()

    _recompute_tree(session, tree)
    session.add(
        AuditLog(
            actor_user_id=admin.id,
            action="sighting.approve",
            target_type="sighting",
            target_id=str(sighting.id),
            payload={"tag": tag, "tree_id": str(tree.id)},
        )
    )
    return tree


def reject(session: Session, sighting: Sighting, admin: User, reason: str) -> None:
    sighting.status = "rejected"
    sighting.reject_reason = reason.strip() or "no reason given"
    sighting.reviewed_at = datetime.now(timezone.utc)
    sighting.reviewed_by = admin.id
    session.add(
        AuditLog(
            actor_user_id=admin.id,
            action="sighting.reject",
            target_type="sighting",
            target_id=str(sighting.id),
            payload={"reason": sighting.reject_reason},
        )
    )


def _recompute_tree(session: Session, tree: Tree) -> None:
    row = session.execute(
        select(
            func.avg(Sighting.lat),
            func.avg(Sighting.lon),
            func.min(Sighting.created_at),
            func.max(Sighting.created_at),
            func.count(Sighting.id),
        ).where(Sighting.tree_id == tree.id, Sighting.status == "approved")
    ).one()
    avg_lat, avg_lon, first_seen, last_seen, count = row
    tree.canonical_lat = float(avg_lat) if avg_lat is not None else None
    tree.canonical_lon = float(avg_lon) if avg_lon is not None else None
    if first_seen:
        tree.first_seen_at = first_seen
    if last_seen:
        tree.last_seen_at = last_seen
    tree.sighting_count = int(count or 0)


def get_pending(session: Session, limit: int = 100) -> list[Sighting]:
    return list(
        session.scalars(
            select(Sighting).where(Sighting.status == "pending").order_by(Sighting.created_at.desc()).limit(limit)
        )
    )


def get_sighting(session: Session, sighting_id: uuid.UUID) -> Sighting | None:
    return session.get(Sighting, sighting_id)
