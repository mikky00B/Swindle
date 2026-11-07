from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.auth.dependencies import require_user_id
from app.auth.service import create_auth_session, set_session_cookie
from app.core.config import get_settings
from app.integrations.lichess.schemas import DisconnectResponse, LichessStatus
from app.integrations.lichess.service import (
    complete_callback,
    create_connect_url,
    disconnect_account,
    get_connected_account,
)

logger = logging.getLogger("swindle.lichess")

router = APIRouter(prefix="/integrations/lichess", tags=["lichess"])


def _get_user_id(request: Request) -> str:
    """Resolve the signed-in user; `?session_id=` stays a dev-only convenience."""
    if get_settings().app_env != "production":
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id
    return require_user_id(request)


@router.get("/connect")
async def connect_lichess(request: Request) -> RedirectResponse:
    user_id = _get_user_id(request)
    logger.info("Starting Lichess OAuth for user_id=%s", user_id)
    return RedirectResponse(create_connect_url(user_id), status_code=302)


@router.get("/connect-url")
async def lichess_connect_url(request: Request) -> dict[str, str]:
    user_id = _get_user_id(request)
    logger.info("Creating Lichess OAuth URL for user_id=%s", user_id)
    return {"url": create_connect_url(user_id)}


@router.get("/callback")
async def lichess_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    settings = get_settings()
    if error:
        logger.warning("Lichess OAuth callback returned error: %s", error)
        return _frontend_redirect({"lichess": "error", "reason": error})
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth callback code or state")

    try:
        logger.info("Processing Lichess OAuth callback")
        result = await complete_callback(code, state)
        logger.info("Lichess OAuth callback succeeded for username=%s", result.get("platform_username"))
    except ValueError as exc:
        logger.warning("Lichess OAuth callback failed: %s", exc)
        return _frontend_redirect({"lichess": "error", "reason": str(exc)})

    if result.get("purpose") == "login":
        # Continue with Lichess: sign the user in right on the callback.
        response = _frontend_redirect({"lichess": "connected", "username": result["platform_username"]})
        set_session_cookie(response, create_auth_session(result["user_id"]))
        return response

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
    logger.info("Lichess disconnect for user_id=%s: disconnected=%s", user_id, disconnected)
    return DisconnectResponse(disconnected=disconnected)


def _frontend_redirect(params: dict[str, str | None]) -> RedirectResponse:
    # Land back in the journal, where OAuth was started from.
    query = urlencode({key: value for key, value in params.items() if value})
    target = f"{get_settings().frontend_origin.rstrip('/')}/journal"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(target, status_code=302)
