"""add card size to published posts

Revision ID: 20260617_0008
Revises: 20260617_0007
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa


revision = "20260617_0008"
down_revision = "20260617_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("published_posts", sa.Column("card_size", sa.String(length=32), nullable=False, server_default="square"))
    op.alter_column("published_posts", "card_size", server_default=None)


def downgrade() -> None:
    op.drop_column("published_posts", "card_size")
