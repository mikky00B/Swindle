"""add cloud eval cache

Revision ID: 20260615_0004
Revises: 20260615_0003
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa


revision = "20260615_0004"
down_revision = "20260615_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("game_metrics", sa.Column("turning_point_fen", sa.Text(), nullable=True))
    op.add_column("game_metrics", sa.Column("turning_point_san", sa.String(length=32), nullable=True))
    op.add_column("game_metrics", sa.Column("lowest_eval_fen", sa.Text(), nullable=True))
    op.add_column("game_metrics", sa.Column("highest_eval_fen", sa.Text(), nullable=True))
    op.add_column("game_metrics", sa.Column("analysis_status", sa.String(length=32), nullable=False, server_default="unavailable"))
    op.alter_column("game_metrics", "analysis_status", server_default=None)

    op.create_table(
        "eval_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("fen_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("raw_fen", sa.Text(), nullable=False),
        sa.Column("eval_cp", sa.Integer(), nullable=True),
        sa.Column("mate", sa.Integer(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_eval_cache_fen_key", "eval_cache", ["fen_key"], unique=True)


def downgrade() -> None:
    op.drop_table("eval_cache")
    op.drop_column("game_metrics", "analysis_status")
    op.drop_column("game_metrics", "highest_eval_fen")
    op.drop_column("game_metrics", "lowest_eval_fen")
    op.drop_column("game_metrics", "turning_point_san")
    op.drop_column("game_metrics", "turning_point_fen")
