from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.integrations.chesscom.client import ChessComClientError
from app.integrations.chesscom.schemas import ChessComLinkRequest, ChessComLinkResponse, ChessComStatus, DisconnectResponse
from app.integrations.chesscom.service import disconnect_chesscom_account, get_chesscom_account, link_chesscom_account

router = APIRouter(prefix="/integrations/chesscom", tags=["chesscom"])


def _get_user_id(request: Request) -> str:
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.post("/link", response_model=ChessComLinkResponse)
async def link_chesscom(payload: ChessComLinkRequest, request: Request) -> ChessComLinkResponse:
    try:
        account = await link_chesscom_account(payload.username, _get_user_id(request))
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
    account = get_chesscom_account(_get_user_id(request))
    if account is None:
        return ChessComStatus(connected=False)
    return ChessComStatus(
        connected=True,
        platform_username=account["platform_username"],
        platform_user_id=account["platform_user_id"],
        last_synced_at=account["last_synced_at"],
        connected_at=account["connected_at"],
    )


@router.post("/disconnect", response_model=DisconnectResponse)
async def chesscom_disconnect(request: Request) -> DisconnectResponse:
    return DisconnectResponse(disconnected=disconnect_chesscom_account(_get_user_id(request)))
