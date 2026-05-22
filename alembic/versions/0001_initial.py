"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("picture_url", sa.Text()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "trees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag_number", sa.String(64), nullable=False, unique=True),
        sa.Column("canonical_lat", sa.Float()),
        sa.Column("canonical_lon", sa.Float()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sighting_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "sightings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tree_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trees.id", ondelete="SET NULL")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("photo_path", sa.Text(), nullable=False),
        sa.Column("thumb_path", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float()),
        sa.Column("lon", sa.Float()),
        sa.Column("gps_source", sa.String(16), nullable=False, server_default="none"),
        sa.Column("detected_tag", sa.String(64)),
        sa.Column("detected_conf", sa.Float()),
        sa.Column("final_tag", sa.String(64)),
        sa.Column("comment", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reject_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_sightings_status_created_at", "sightings", ["status", "created_at"])
    op.create_index("ix_sightings_tree_id", "sightings", ["tree_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(32)),
        sa.Column("target_id", sa.String(64)),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("ix_sightings_tree_id", table_name="sightings")
    op.drop_index("ix_sightings_status_created_at", table_name="sightings")
    op.drop_table("sightings")
    op.drop_table("trees")
    op.drop_table("users")
