"""initial persistence

Revision ID: 20260614_0001
Revises: 
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa


revision = "20260614_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=255), primary_key=True),
        sa.Column("code_verifier", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chess_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("platform_user_id", sa.String(length=120), nullable=False),
        sa.Column("platform_username", sa.String(length=120), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_game_id", sa.String(length=120), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "platform", name="uq_chess_accounts_user_platform"),
    )
    op.create_index("ix_chess_accounts_user_id", "chess_accounts", ["user_id"])

    op.create_table(
        "games",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chess_account_id", sa.String(length=36), sa.ForeignKey("chess_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("external_game_id", sa.String(length=120), nullable=False),
        sa.Column("pgn", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("white_username", sa.String(length=120), nullable=True),
        sa.Column("black_username", sa.String(length=120), nullable=True),
        sa.Column("user_color", sa.String(length=16), nullable=True),
        sa.Column("opponent_username", sa.String(length=120), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("winner_color", sa.String(length=16), nullable=True),
        sa.Column("termination", sa.String(length=120), nullable=True),
        sa.Column("rated", sa.Boolean(), nullable=True),
        sa.Column("speed", sa.String(length=32), nullable=True),
        sa.Column("time_control", sa.String(length=32), nullable=True),
        sa.Column("opening_name", sa.Text(), nullable=True),
        sa.Column("opening_eco", sa.String(length=16), nullable=True),
        sa.Column("moves_count", sa.Integer(), nullable=False),
        sa.Column("user_rating_before", sa.Integer(), nullable=True),
        sa.Column("user_rating_after", sa.Integer(), nullable=True),
        sa.Column("opponent_rating", sa.Integer(), nullable=True),
        sa.Column("rating_change", sa.Integer(), nullable=True),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "platform", "external_game_id", name="uq_games_user_platform_external"),
    )
    op.create_index("ix_games_user_id", "games", ["user_id"])
    op.create_index("ix_games_chess_account_id", "games", ["chess_account_id"])
    op.create_index("ix_games_played_at", "games", ["played_at"])

    op.create_table(
        "game_metrics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("lowest_eval", sa.Float(), nullable=True),
        sa.Column("highest_eval", sa.Float(), nullable=True),
        sa.Column("biggest_eval_swing", sa.Float(), nullable=True),
        sa.Column("turning_point_move", sa.Integer(), nullable=True),
        sa.Column("blunders_count", sa.Integer(), nullable=True),
        sa.Column("mistakes_count", sa.Integer(), nullable=True),
        sa.Column("inaccuracies_count", sa.Integer(), nullable=True),
        sa.Column("captures_count", sa.Integer(), nullable=True),
        sa.Column("checks_count", sa.Integer(), nullable=True),
        sa.Column("user_lowest_clock_seconds", sa.Integer(), nullable=True),
        sa.Column("moves_under_time_pressure", sa.Integer(), nullable=True),
        sa.Column("eval_curve", sa.JSON(), nullable=True),
        sa.Column("analysis_depth", sa.Integer(), nullable=True),
        sa.Column("analysis_source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_game_metrics_game_id", "game_metrics", ["game_id"], unique=True)

    op.create_table(
        "game_stories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("primary_story", sa.String(length=80), nullable=False),
        sa.Column("secondary_story", sa.String(length=80), nullable=True),
        sa.Column("badge_label", sa.String(length=120), nullable=False),
        sa.Column("badge_emoji", sa.String(length=16), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("subheadline", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("mood", sa.String(length=80), nullable=True),
        sa.Column("key_move_number", sa.Integer(), nullable=True),
        sa.Column("key_position_fen", sa.Text(), nullable=True),
        sa.Column("key_move_san", sa.String(length=32), nullable=True),
        sa.Column("key_move_from", sa.String(length=8), nullable=True),
        sa.Column("key_move_to", sa.String(length=8), nullable=True),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("interesting_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("share_card_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_game_stories_game_id", "game_stories", ["game_id"], unique=True)
    op.create_index("ix_game_stories_user_id", "game_stories", ["user_id"])


def downgrade() -> None:
    op.drop_table("game_stories")
    op.drop_table("game_metrics")
    op.drop_table("games")
    op.drop_table("chess_accounts")
    op.drop_table("oauth_states")
    op.drop_table("users")
