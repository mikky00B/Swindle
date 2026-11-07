from __future__ import annotations

from fastapi import HTTPException, Request

from app.auth.service import SESSION_COOKIE_NAME, user_id_for_token
from app.core.config import get_settings


def resolve_user_id(request: Request) -> str | None:
    """Cookie-backed identity; header fallback only outside production.

    The X-Session-Id fallback keeps local development and the existing test
    suite working without accounts. It is disabled in production, where the
    signed-in user is identified exclusively by the auth session cookie.
    """
    user_id = user_id_for_token(request.cookies.get(SESSION_COOKIE_NAME))
    if user_id:
        return user_id
    if get_settings().app_env != "production":
        session_id = request.headers.get("X-Session-Id")
        return session_id or "local-dev-user"
    return None


def resolve_user_id_strict(request: Request) -> str | None:
    """Cookie-only identity, used by /auth/me to reflect real sign-in state."""
    return user_id_for_token(request.cookies.get(SESSION_COOKIE_NAME))


def require_user_id(request: Request) -> str:
    user_id = resolve_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
