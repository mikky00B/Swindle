"""add card theme to published posts

Revision ID: 20260617_0007
Revises: 20260615_0006
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa


revision = "20260617_0007"
down_revision = "20260615_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("published_posts", sa.Column("card_theme", sa.String(length=32), nullable=False, server_default="classic"))
    op.alter_column("published_posts", "card_theme", server_default=None)


def downgrade() -> None:
    op.drop_column("published_posts", "card_theme")
