from __future__ import annotations

import hashlib
import secrets
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import get_session
from app.models import AuthSession, User

SESSION_COOKIE_NAME = "swindle_session"
SESSION_TTL_DAYS = 30
MAX_PASSWORD_BYTES = 72  # bcrypt only considers the first 72 bytes
AUTH_ATTEMPT_LIMIT = 10
AUTH_ATTEMPT_WINDOW_SECONDS = 300

_recent_auth_attempts: dict[str, deque[datetime]] = {}


class AuthError(ValueError):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_credentials(username: str, password: str) -> tuple[str, str]:
    name = (username or "").strip()
    if not 3 <= len(name) <= 40 or not all(char.isalnum() or char in "-_" for char in name):
        raise AuthError("Username must be 3-40 letters, numbers, dashes, or underscores.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AuthError("Password must be at most 72 bytes.")
    return name, password


def auth_attempt_allowed(key: str) -> bool:
    """Sliding in-memory rate limit for auth attempts. Good enough for v1."""
    now = datetime.now(timezone.utc)
    attempts = _recent_auth_attempts.setdefault(key, deque())
    while attempts and (now - attempts[0]).total_seconds() > AUTH_ATTEMPT_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= AUTH_ATTEMPT_LIMIT:
        return False
    attempts.append(now)
    return True


def register_user(username: str, password: str) -> User:
    name, validated_password = validate_credentials(username, password)
    with get_session() as session:
        existing = session.scalar(select(User).where(func.lower(User.username) == name.lower()))
        if existing is not None:
            raise AuthError("That username is already taken.")
        user = User(username=name, password_hash=hash_password(validated_password))
        session.add(user)
        try:
            session.flush()
        except IntegrityError as exc:
            raise AuthError("That username is already taken.") from exc
        return user


def authenticate_user(username: str, password: str) -> User | None:
    candidate = (username or "").strip()
    with get_session() as session:
        user = session.scalar(select(User).where(func.lower(User.username) == candidate.lower()))
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user


def get_user(user_id: str) -> User | None:
    with get_session() as session:
        return session.get(User, user_id)


def create_auth_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    with get_session() as session:
        session.add(AuthSession(user_id=user_id, token_hash=_token_hash(token), expires_at=expires_at))
    return token


def user_id_for_token(token: str | None) -> str | None:
    if not token:
        return None
    with get_session() as session:
        record = session.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        if record is None:
            return None
        user_id = record.user_id
        expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return user_id


def revoke_auth_session(token: str | None) -> bool:
    if not token:
        return False
    with get_session() as session:
        record = session.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        if record is None:
            return False
        session.delete(record)
    return True


def set_session_cookie(response: Any, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Any) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
