from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uuid_str() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chess_accounts: Mapped[list[ChessAccount]] = relationship(back_populates="user")
    games: Mapped[list[Game]] = relationship(back_populates="user")


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(255), primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChessAccount(Base):
    __tablename__ = "chess_accounts"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_chess_accounts_user_platform"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="lichess")
    platform_user_id: Mapped[str] = mapped_column(String(120))
    platform_username: Mapped[str] = mapped_column(String(120))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_game_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="chess_accounts")
    games: Mapped[list[Game]] = relationship(back_populates="chess_account")


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "external_game_id", name="uq_games_user_platform_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chess_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("chess_accounts.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="lichess")
    external_game_id: Mapped[str] = mapped_column(String(120))
    pgn: Mapped[str] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    white_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    black_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    opponent_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[str] = mapped_column(String(32))
    winner_color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    termination: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    speed: Mapped[str | None] = mapped_column(String(32), nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(32), nullable=True)
    opening_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String(16), nullable=True)
    moves_count: Mapped[int] = mapped_column(Integer, default=0)
    user_rating_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_rating_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opponent_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_change: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    final_fen: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processing_status: Mapped[str] = mapped_column(String(32), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="games")
    chess_account: Mapped[ChessAccount] = relationship(back_populates="games")
    story: Mapped[GameStory | None] = relationship(back_populates="game", uselist=False, cascade="all, delete-orphan")
    metrics: Mapped[GameMetric | None] = relationship(back_populates="game", uselist=False, cascade="all, delete-orphan")


class GameMetric(Base):
    __tablename__ = "game_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), unique=True, index=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    lowest_eval: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_eval: Mapped[float | None] = mapped_column(Float, nullable=True)
    biggest_eval_swing: Mapped[float | None] = mapped_column(Float, nullable=True)
    turning_point_move: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turning_point_fen: Mapped[str | None] = mapped_column(Text, nullable=True)
    turning_point_san: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lowest_eval_fen: Mapped[str | None] = mapped_column(Text, nullable=True)
    highest_eval_fen: Mapped[str | None] = mapped_column(Text, nullable=True)
    blunders_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mistakes_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inaccuracies_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captures_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_lowest_clock_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moves_under_time_pressure: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eval_curve: Mapped[list | None] = mapped_column(JSON, nullable=True)
    analysis_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_source: Mapped[str] = mapped_column(String(32), default="metadata_only")
    analysis_status: Mapped[str] = mapped_column(String(32), default="unavailable")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    game: Mapped[Game] = relationship(back_populates="metrics")


class GameStory(Base):
    __tablename__ = "game_stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    primary_story: Mapped[str] = mapped_column(String(80))
    secondary_story: Mapped[str | None] = mapped_column(String(80), nullable=True)
    badge_label: Mapped[str] = mapped_column(String(120))
    badge_emoji: Mapped[str] = mapped_column(String(16))
    headline: Mapped[str] = mapped_column(Text)
    subheadline: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(80), nullable=True)
    key_move_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_position_fen: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_move_san: Mapped[str | None] = mapped_column(String(32), nullable=True)
    key_move_from: Mapped[str | None] = mapped_column(String(8), nullable=True)
    key_move_to: Mapped[str | None] = mapped_column(String(8), nullable=True)
    template_key: Mapped[str] = mapped_column(String(120))
    interesting_score: Mapped[float] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    share_card_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    game: Mapped[Game] = relationship(back_populates="story")


class SuggestedPost(Base):
    __tablename__ = "suggested_posts"
    __table_args__ = (
        UniqueConstraint("user_id", "game_story_id", name="uq_suggested_posts_user_story"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    game_story_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_stories.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EvalCache(Base):
    __tablename__ = "eval_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    fen_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    raw_fen: Mapped[str] = mapped_column(Text)
    eval_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="lichess_cloud_eval")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PublishedPost(Base):
    __tablename__ = "published_posts"
    __table_args__ = (
        UniqueConstraint("user_id", "game_story_id", name="uq_published_posts_user_story"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    game_story_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_stories.id", ondelete="CASCADE"), index=True)
    headline: Mapped[str] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    card_theme: Mapped[str] = mapped_column(String(32), default="classic")
    card_size: Mapped[str] = mapped_column(String(32), default="square")
    visibility: Mapped[str] = mapped_column(String(32), default="public", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    game: Mapped[Game] = relationship()
    game_story: Mapped[GameStory] = relationship()


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    games_count: Mapped[int] = mapped_column(Integer)
    wins_count: Mapped[int] = mapped_column(Integer, default=0)
    losses_count: Mapped[int] = mapped_column(Integer, default=0)
    draws_count: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0)
    best_story_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    best_game_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("games.id", ondelete="SET NULL"), nullable=True)
    best_game_story_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("game_stories.id", ondelete="SET NULL"), nullable=True)
    most_common_opening: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary_headline: Mapped[str] = mapped_column(Text)
    summary_subheadline: Mapped[str | None] = mapped_column(Text, nullable=True)
    swindle_count: Mapped[int] = mapped_column(Integer, default=0)
    heartbreaker_count: Mapped[int] = mapped_column(Integer, default=0)
    miniature_count: Mapped[int] = mapped_column(Integer, default=0)
    long_grind_count: Mapped[int] = mapped_column(Integer, default=0)
    giant_slayer_count: Mapped[int] = mapped_column(Integer, default=0)
    turning_point_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    games: Mapped[list[GameSessionGame]] = relationship(back_populates="session", cascade="all, delete-orphan")
    best_game: Mapped[Game | None] = relationship(foreign_keys=[best_game_id])
    best_game_story: Mapped[GameStory | None] = relationship(foreign_keys=[best_game_story_id])


class GameSessionGame(Base):
    __tablename__ = "game_session_games"
    __table_args__ = (UniqueConstraint("session_id", "game_id", name="uq_game_session_games_session_game"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[GameSession] = relationship(back_populates="games")
    game: Mapped[Game] = relationship()


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_follows_follower_following"),
        CheckConstraint("follower_id != following_id", name="ck_follows_not_self"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    follower_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    following_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Kudos(Base):
    __tablename__ = "kudos"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", "type", name="uq_kudos_post_user_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("published_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32), default="kudos")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("published_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
