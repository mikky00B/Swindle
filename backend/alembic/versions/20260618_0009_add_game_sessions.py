"""add game sessions

Revision ID: 20260618_0009
Revises: 20260617_0008
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa


revision = "20260618_0009"
down_revision = "20260617_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("games_count", sa.Integer(), nullable=False),
        sa.Column("wins_count", sa.Integer(), nullable=False),
        sa.Column("losses_count", sa.Integer(), nullable=False),
        sa.Column("draws_count", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("best_story_type", sa.String(length=80), nullable=True),
        sa.Column("best_game_id", sa.String(length=36), sa.ForeignKey("games.id", ondelete="SET NULL"), nullable=True),
        sa.Column("best_game_story_id", sa.String(length=36), sa.ForeignKey("game_stories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("most_common_opening", sa.Text(), nullable=True),
        sa.Column("rating_delta", sa.Integer(), nullable=True),
        sa.Column("mood", sa.String(length=80), nullable=True),
        sa.Column("summary_headline", sa.Text(), nullable=False),
        sa.Column("summary_subheadline", sa.Text(), nullable=True),
        sa.Column("swindle_count", sa.Integer(), nullable=False),
        sa.Column("heartbreaker_count", sa.Integer(), nullable=False),
        sa.Column("miniature_count", sa.Integer(), nullable=False),
        sa.Column("long_grind_count", sa.Integer(), nullable=False),
        sa.Column("giant_slayer_count", sa.Integer(), nullable=False),
        sa.Column("turning_point_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_game_sessions_user_id", "game_sessions", ["user_id"])
    op.create_index("ix_game_sessions_started_at", "game_sessions", ["started_at"])
    op.create_index("ix_game_sessions_ended_at", "game_sessions", ["ended_at"])
    op.create_table(
        "game_session_games",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "game_id", name="uq_game_session_games_session_game"),
    )
    op.create_index("ix_game_session_games_session_id", "game_session_games", ["session_id"])
    op.create_index("ix_game_session_games_game_id", "game_session_games", ["game_id"])


def downgrade() -> None:
    op.drop_table("game_session_games")
    op.drop_table("game_sessions")
