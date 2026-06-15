from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import decrypt_token, encrypt_token
from app.integrations.lichess.oauth import (
    build_authorize_url,
    code_challenge_s256,
    generate_code_verifier,
    generate_state,
    oauth_state_expiry,
)
from app.models import ChessAccount, OAuthState, User

LOCAL_USER_ID = "local-dev-user"
LOCAL_USERNAME = "local"


def create_connect_url(user_id: str = LOCAL_USER_ID) -> str:
    state = generate_state()
    verifier = generate_code_verifier()
    with get_session() as session:
        ensure_local_user(session, user_id)
        session.add(
            OAuthState(
                state=state,
                code_verifier=verifier,
                user_id=user_id,
                expires_at=oauth_state_expiry(),
            )
        )
    return build_authorize_url(state, code_challenge_s256(verifier))


async def complete_callback(code: str, state: str) -> dict[str, Any]:
    state_record = _consume_state(state)
    if state_record is None:
        raise ValueError("Invalid or expired OAuth state")

    try:
        token_payload = await exchange_code_for_token(code, state_record["code_verifier"])
    except httpx.HTTPStatusError as exc:
        detail = _response_text(exc.response)
        raise ValueError(f"Lichess token exchange failed ({exc.response.status_code}): {detail}") from exc
    except httpx.HTTPError as exc:
        raise ValueError("Could not reach Lichess while exchanging the OAuth code.") from exc
    access_token = token_payload.get("access_token")
    if not access_token:
        raise ValueError("Lichess token response did not include an access token")

    try:
        account = await fetch_account(access_token)
    except httpx.HTTPStatusError as exc:
        detail = _response_text(exc.response)
        raise ValueError(f"Lichess account lookup failed ({exc.response.status_code}): {detail}") from exc
    except httpx.HTTPError as exc:
        raise ValueError("Could not reach Lichess while fetching the connected account.") from exc
    user_id = state_record["user_id"]
    account_id = store_connected_account(user_id, token_payload, account)
    return {"account_id": account_id, "platform_username": account.get("username")}


async def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.post(
            settings.lichess_oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.lichess_redirect_uri,
                "client_id": settings.lichess_client_id,
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_account(access_token: str) -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.get(
            lichess_api_url("/account"),
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def store_connected_account(user_id: str, token_payload: dict[str, Any], account: dict[str, Any]) -> str:
    settings = get_settings()
    scopes = _scopes_from_token(token_payload)
    now = datetime.now(timezone.utc)
    platform_user_id = str(account.get("id") or account.get("username"))
    platform_username = str(account.get("username") or account.get("id"))
    encrypted = encrypt_token(str(token_payload["access_token"]), settings.token_encryption_key)

    with get_session() as session:
        ensure_local_user(session, user_id)
        existing = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "lichess")
        )
        if existing:
            existing.platform_user_id = platform_user_id
            existing.platform_username = platform_username
            existing.access_token_encrypted = encrypted
            existing.scopes = scopes
            existing.connected_at = now
            account_id = existing.id
        else:
            chess_account = ChessAccount(
                user_id=user_id,
                platform="lichess",
                platform_user_id=platform_user_id,
                platform_username=platform_username,
                access_token_encrypted=encrypted,
                scopes=scopes,
                connected_at=now,
            )
            session.add(chess_account)
            session.flush()
            account_id = chess_account.id
    return account_id


def get_connected_account(user_id: str = LOCAL_USER_ID) -> dict[str, Any] | None:
    with get_session() as session:
        account = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "lichess")
        )
        if account is None:
            return None
        return _account_to_dict(account)


def get_decrypted_access_token(account: dict[str, Any]) -> str:
    return decrypt_token(account["access_token_encrypted"], get_settings().token_encryption_key)


def disconnect_account(user_id: str = LOCAL_USER_ID) -> bool:
    with get_session() as session:
        account = session.scalar(
            select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "lichess")
        )
        if account is None:
            return False
        session.delete(account)
    return True


def _consume_state(state: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        record = session.get(OAuthState, state)
        if record is None:
            return None
        state_data = {
            "state": record.state,
            "code_verifier": record.code_verifier,
            "user_id": record.user_id,
            "expires_at": record.expires_at,
        }
        session.delete(record)
    expires_at = state_data["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return None
    return state_data


def _scopes_from_token(token_payload: dict[str, Any]) -> list[str]:
    scope = token_payload.get("scope")
    if isinstance(scope, str):
        return [item for item in scope.split(" ") if item]
    return [item for item in get_settings().lichess_scopes.split(" ") if item]


def lichess_api_url(path: str) -> str:
    base = get_settings().lichess_api_base_url.rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return f"{base}/{path.lstrip('/')}"


def _response_text(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        return "no response body"
    return text[:240]


def ensure_local_user(session, user_id: str = LOCAL_USER_ID) -> User:
    user = session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=_local_username(user_id))
        session.add(user)
        session.flush()
    return user


def _local_username(user_id: str) -> str:
    if user_id == LOCAL_USER_ID:
        return LOCAL_USERNAME
    safe_user_id = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in user_id)
    return f"{LOCAL_USERNAME}-{safe_user_id}"[:80]


def _account_to_dict(account: ChessAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "user_id": account.user_id,
        "platform": account.platform,
        "platform_user_id": account.platform_user_id,
        "platform_username": account.platform_username,
        "access_token_encrypted": account.access_token_encrypted,
        "scopes": account.scopes or [],
        "connected_at": account.connected_at.isoformat(),
    }
