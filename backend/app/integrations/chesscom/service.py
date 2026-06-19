from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.database import get_session
from app.integrations.chesscom.client import ChessComClient
from app.integrations.lichess.service import LOCAL_USER_ID, ensure_local_user
from app.models import ChessAccount


async def link_chesscom_account(username: str, user_id: str = LOCAL_USER_ID) -> dict[str, Any]:
    profile = await ChessComClient().get_player(username)
    platform_username = str(profile.get("username") or username).strip()
    if not platform_username:
        raise ValueError("Chess.com username not found.")
    now = datetime.now(timezone.utc)
    with get_session() as session:
        ensure_local_user(session, user_id)
        existing = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "chesscom")
        )
        if existing:
            existing.platform_user_id = str(profile.get("player_id") or platform_username)
            existing.platform_username = platform_username
            existing.raw_profile = profile
            existing.scopes = []
            existing.access_token_encrypted = None
            existing.refresh_token_encrypted = None
            existing.token_expires_at = None
            existing.connected_at = now
            existing.updated_at = now
            account = existing
        else:
            account = ChessAccount(
                user_id=user_id,
                platform="chesscom",
                platform_user_id=str(profile.get("player_id") or platform_username),
                platform_username=platform_username,
                access_token_encrypted=None,
                refresh_token_encrypted=None,
                scopes=[],
                raw_profile=profile,
                connected_at=now,
            )
            session.add(account)
            session.flush()
        return _account_to_dict(account)


def get_chesscom_account(user_id: str = LOCAL_USER_ID) -> dict[str, Any] | None:
    with get_session() as session:
        account = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "chesscom")
        )
        if account is None:
            return None
        return _account_to_dict(account)


def disconnect_chesscom_account(user_id: str = LOCAL_USER_ID) -> bool:
    with get_session() as session:
        account = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "chesscom")
        )
        if account is None:
            return False
        session.delete(account)
    return True


def mark_chesscom_synced(user_id: str, last_seen_game_id: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        account = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "chesscom")
        )
        if account is None:
            return
        account.last_synced_at = now
        if last_seen_game_id:
            account.last_seen_game_id = last_seen_game_id
        account.updated_at = now


def _account_to_dict(account: ChessAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "user_id": account.user_id,
        "platform": account.platform,
        "platform_user_id": account.platform_user_id,
        "platform_username": account.platform_username,
        "raw_profile": account.raw_profile or {},
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
        "connected_at": account.connected_at.isoformat(),
    }
