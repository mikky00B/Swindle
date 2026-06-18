from fastapi import APIRouter, HTTPException, Request

from app.sessions.processor import get_session_detail, get_session_share_card, list_sessions, rebuild_user_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_user_id(request: Request) -> str:
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.get("")
async def recent_sessions(request: Request) -> list[dict]:
    return list_sessions(_get_user_id(request))


@router.post("/rebuild")
async def rebuild_sessions(request: Request) -> dict:
    return rebuild_user_sessions(_get_user_id(request))


@router.get("/{session_id}")
async def session_detail(session_id: str, request: Request) -> dict:
    result = get_session_detail(session_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/{session_id}/share-card")
async def session_share_card(session_id: str, request: Request) -> dict:
    result = get_session_share_card(session_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
