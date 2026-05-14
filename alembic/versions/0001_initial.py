"""Initial migration — creates users, videos, and locations tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(32), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=True),
        sa.Column("google_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "videos",
        sa.Column("id", sa.CHAR(32), primary_key=True),
        sa.Column("farmer_id", sa.CHAR(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("raw_path", sa.String(500), nullable=True),
        sa.Column("processed_path", sa.String(500), nullable=True),
        sa.Column("thumbnail_path", sa.String(500), nullable=True),
        sa.Column("title_az", sa.Text(), nullable=True),
        sa.Column("title_en", sa.Text(), nullable=True),
        sa.Column("title_ar", sa.Text(), nullable=True),
        sa.Column("hashtags_az", sa.Text(), nullable=True),
        sa.Column("hashtags_en", sa.Text(), nullable=True),
        sa.Column("hashtags_ar", sa.Text(), nullable=True),
        sa.Column("instagram_media_id", sa.String(100), nullable=True),
        sa.Column("instagram_permalink", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("stabilized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audio_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_videos_farmer_id", "videos", ["farmer_id"])
    op.create_index("ix_videos_id", "videos", ["id"])

    op.create_table(
        "locations",
        sa.Column("id", sa.CHAR(32), primary_key=True),
        sa.Column("video_id", sa.CHAR(32), sa.ForeignKey("videos.id"), nullable=False, unique=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_locations_video_id", "locations", ["video_id"])


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_table("videos")
    op.drop_table("users")
