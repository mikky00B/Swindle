"""Chess.com OAuth: link a Chess.com account to a signed-in user.

Chess.com's OAuth has no identity endpoint, so the flow is "verify and
link": the user types their Chess.com username, the OAuth step proves
they own it, and the encrypted token upgrades the public-archive link to
an authorized one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import encrypt_token
from app.integrations.lichess.oauth import code_challenge_s256, generate_code_verifier, generate_state, oauth_state_expiry
from app.integrations.lichess.service import _consume_state
from app.models import ChessAccount, OAuthState, User


def chesscom_oauth_enabled() -> bool:
    settings = get_settings()
    return bool(settings.chesscom_client_id and settings.chesscom_client_secret)


def create_chesscom_connect_url(user_id: str, username: str) -> str:
    """Authorize URL for linking `username`'s Chess.com account to `user_id`."""
    settings = get_settings()
    state = generate_state()
    verifier = generate_code_verifier()
    with get_session() as session:
        session.add(
            OAuthState(
                state=state,
                code_verifier=verifier,
                purpose="bind",
                platform="chesscom",
                username=username,
                user_id=user_id,
                expires_at=oauth_state_expiry(),
            )
        )
    params = {
        "response_type": "code",
        "client_id": settings.chesscom_client_id,
        "redirect_uri": settings.chesscom_redirect_uri,
        "state": state,
        "code_challenge": code_challenge_s256(verifier),
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{key}={_urlsafe(value)}" for key, value in params.items())
    return f"{settings.chesscom_oauth_authorize_url}?{query}"


def _urlsafe(value: str) -> str:
    from urllib.parse import quote

    return quote(str(value), safe="")


async def complete_chesscom_callback(code: str, state: str) -> dict[str, Any]:
    """Exchange the code, verify the linked username, store the encrypted token."""
    state_record = _consume_state(state)
    if state_record is None or state_record.get("platform") != "chesscom":
        raise ValueError("Invalid or expired OAuth state")
    user_id = state_record.get("user_id")
    username = state_record.get("username")
    if not user_id or not username:
        raise ValueError("Invalid or expired OAuth state")

    token_payload = await exchange_code_for_token(code, state_record["code_verifier"])
    access_token = token_payload.get("access_token")
    if not access_token:
        raise ValueError("Chess.com token response did not include an access token")

    account_id = store_chesscom_oauth_account(user_id, username, token_payload)
    return {"account_id": account_id, "username": username, "user_id": user_id}


async def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.post(
            settings.chesscom_oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.chesscom_redirect_uri,
                "client_id": settings.chesscom_client_id,
                "client_secret": settings.chesscom_client_secret,
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def store_chesscom_oauth_account(user_id: str, username: str, token_payload: dict[str, Any]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    encrypted = encrypt_token(str(token_payload["access_token"]), settings.token_encryption_key)

    with get_session() as session:
        if session.get(User, user_id) is None:
            raise ValueError("Invalid or expired OAuth state")
        existing = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "chesscom")
        )
        if existing is None:
            account = ChessAccount(
                user_id=user_id,
                platform="chesscom",
                platform_user_id=username,
                platform_username=username,
                access_token_encrypted=encrypted,
                connected_at=now,
            )
            session.add(account)
            session.flush()
            account_id = account.id
        else:
            existing.platform_user_id = username
            existing.platform_username = username
            existing.access_token_encrypted = encrypted
            existing.connected_at = now
            account_id = existing.id
    return account_id


def username_taken_by_other(username: str, user_id: str) -> bool:
    lowered = username.strip().lower()
    with get_session() as session:
        row = session.scalar(
            select(ChessAccount).where(
                ChessAccount.platform == "chesscom",
                func.lower(ChessAccount.platform_username) == lowered,
            )
        )
    return row is not None and row.user_id != user_id
