from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
