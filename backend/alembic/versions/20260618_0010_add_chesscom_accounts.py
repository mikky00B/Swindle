"""add chesscom account support

Revision ID: 20260618_0010
Revises: 20260618_0009
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0010"
down_revision = "20260618_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("chess_accounts", "access_token_encrypted", existing_type=sa.Text(), nullable=True)
    op.add_column("chess_accounts", sa.Column("raw_profile", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("chess_accounts", "raw_profile")
    op.alter_column("chess_accounts", "access_token_encrypted", existing_type=sa.Text(), nullable=False)
