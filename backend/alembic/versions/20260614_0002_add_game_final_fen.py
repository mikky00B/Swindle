"""add game final fen

Revision ID: 20260614_0002
Revises: 20260614_0001
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa


revision = "20260614_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("final_fen", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "final_fen")
