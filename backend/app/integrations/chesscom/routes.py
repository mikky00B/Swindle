from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.auth.dependencies import require_user_id
from app.core.config import get_settings
from app.integrations.chesscom.client import ChessComClientError
from app.integrations.chesscom.oauth import (
    chesscom_oauth_enabled,
    complete_chesscom_callback,
    create_chesscom_connect_url,
    username_taken_by_other,
)
from app.integrations.chesscom.schemas import ChessComLinkRequest, ChessComLinkResponse, ChessComStatus, DisconnectResponse
from app.integrations.chesscom.service import disconnect_chesscom_account, get_chesscom_account, link_chesscom_account

router = APIRouter(prefix="/integrations/chesscom", tags=["chesscom"])


@router.get("/connect")
async def connect_chesscom(request: Request, username: str = Query(min_length=1)) -> RedirectResponse:
    """Begin the Chess.com OAuth link for the signed-in user and username."""
    if not chesscom_oauth_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    user_id = require_user_id(request)
    username = username.strip()
    if username_taken_by_other(username, user_id):
        raise HTTPException(status_code=400, detail="That Chess.com username is already linked to another account")
    return RedirectResponse(create_chesscom_connect_url(user_id, username), status_code=302)


@router.get("/callback")
async def chesscom_callback(code: str | None = None, state: str | None = None) -> RedirectResponse:
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback code or state")
    try:
        result = await complete_chesscom_callback(code, state)
    except ValueError as exc:
        return _frontend_redirect({"chesscom": "error", "reason": str(exc)})
    return _frontend_redirect({"chesscom": "connected", "username": result["username"]})


def _frontend_redirect(params: dict[str, str | None]) -> RedirectResponse:
    query = urlencode({key: value for key, value in params.items() if value})
    target = f"{get_settings().frontend_origin.rstrip('/')}/journal"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(target, status_code=302)


@router.post("/link", response_model=ChessComLinkResponse)
async def link_chesscom(payload: ChessComLinkRequest, request: Request) -> ChessComLinkResponse:
    try:
        account = await link_chesscom_account(payload.username, require_user_id(request))
    except ChessComClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ChessComLinkResponse(
        connected=True,
        platform_username=account["platform_username"],
        platform_user_id=account["platform_user_id"],
        last_synced_at=account["last_synced_at"],
        connected_at=account["connected_at"],
    )


@router.get("/status", response_model=ChessComStatus)
async def chesscom_status(request: Request) -> ChessComStatus:
    account = get_chesscom_account(require_user_id(request))
    if account is None:
        return ChessComStatus(connected=False, oauth_enabled=chesscom_oauth_enabled())
    return ChessComStatus(
        connected=True,
        platform_username=account["platform_username"],
        platform_user_id=account["platform_user_id"],
        last_synced_at=account["last_synced_at"],
        connected_at=account["connected_at"],
        oauth_enabled=chesscom_oauth_enabled(),
    )


@router.post("/disconnect", response_model=DisconnectResponse)
async def chesscom_disconnect(request: Request) -> DisconnectResponse:
    return DisconnectResponse(disconnected=disconnect_chesscom_account(require_user_id(request)))
