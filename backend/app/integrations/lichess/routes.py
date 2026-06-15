from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.integrations.lichess.schemas import DisconnectResponse, LichessStatus
from app.integrations.lichess.service import (
    complete_callback,
    create_connect_url,
    disconnect_account,
    get_connected_account,
)

router = APIRouter(prefix="/integrations/lichess", tags=["lichess"])


def _get_user_id(request: Request) -> str:
    """Extract user_id from X-Session-Id header (browser session isolation)"""
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.get("/connect")
async def connect_lichess(request: Request) -> RedirectResponse:
    user_id = _get_user_id(request)
    print(f"[CONNECT] Starting OAuth for user_id: {user_id}")
    return RedirectResponse(create_connect_url(user_id), status_code=302)


@router.get("/connect-url")
async def lichess_connect_url(request: Request) -> dict[str, str]:
    user_id = _get_user_id(request)
    print(f"[CONNECT] Creating OAuth URL for user_id: {user_id}")
    return {"url": create_connect_url(user_id)}


@router.get("/callback")
async def lichess_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    settings = get_settings()
    if error:
        print(f"[CALLBACK] OAuth error: {error}")
        return _frontend_redirect({"lichess": "error", "reason": error})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback code or state")

    try:
        print(f"[CALLBACK] Processing OAuth callback with state: {state[:20]}...")
        result = await complete_callback(code, state)
        print(f"[CALLBACK] OAuth callback succeeded. Username: {result.get('platform_username')}")
    except ValueError as exc:
        print(f"[CALLBACK] OAuth callback failed: {exc}")
        return _frontend_redirect({"lichess": "error", "reason": str(exc)})

    return _frontend_redirect({"lichess": "connected", "username": result["platform_username"]})


@router.get("/status", response_model=LichessStatus)
async def lichess_status(request: Request) -> LichessStatus:
    user_id = _get_user_id(request)
    account = get_connected_account(user_id)
    if account is None:
        return LichessStatus(connected=False)
    return LichessStatus(
        connected=True,
        platform_username=account["platform_username"],
        platform_user_id=account["platform_user_id"],
        scopes=account["scopes"],
        connected_at=account["connected_at"],
    )


@router.post("/disconnect", response_model=DisconnectResponse)
async def lichess_disconnect(request: Request) -> DisconnectResponse:
    user_id = _get_user_id(request)
    disconnected = disconnect_account(user_id)
    print(f"[DISCONNECT] user_id: {user_id}, disconnected: {disconnected}")
    return DisconnectResponse(disconnected=disconnected)


def _frontend_redirect(params: dict[str, str | None]) -> RedirectResponse:
    query = urlencode({key: value for key, value in params.items() if value})
    return RedirectResponse(f"{get_settings().frontend_origin}?{query}", status_code=302)
