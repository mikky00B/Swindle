"""add published posts

Revision ID: 20260615_0005
Revises: 20260615_0004
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa


revision = "20260615_0005"
down_revision = "20260615_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "published_posts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_story_id", sa.String(length=36), sa.ForeignKey("game_stories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "game_story_id", name="uq_published_posts_user_story"),
    )
    op.create_index("ix_published_posts_user_id", "published_posts", ["user_id"])
    op.create_index("ix_published_posts_game_id", "published_posts", ["game_id"])
    op.create_index("ix_published_posts_game_story_id", "published_posts", ["game_story_id"])
    op.create_index("ix_published_posts_visibility", "published_posts", ["visibility"])


def downgrade() -> None:
    op.drop_table("published_posts")
