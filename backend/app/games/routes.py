from fastapi import APIRouter, HTTPException, Query, Request

from app.core.config import get_settings
from app.games.schemas import DebugEvalRequest
from app.games.lichess_import import import_latest_lichess_games
from app.games.repository import (
    debug_eval_game,
    get_game_debug,
    get_imported_game_detail,
    get_share_card,
    list_imported_games,
    reprocess_all_games,
    reprocess_game,
)
from app.integrations.lichess.schemas import LichessImportResponse
from app.share_cards.schemas import ShareCardData

router = APIRouter(prefix="/games", tags=["games"])


def _get_user_id(request: Request) -> str:
    """Extract user_id from X-Session-Id header (browser session isolation)"""
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.get("")
async def games_journal(request: Request) -> list[dict]:
    user_id = _get_user_id(request)
    return list_imported_games(user_id)


@router.get("/{game_id}")
async def game_detail(game_id: str, request: Request) -> dict:
    user_id = _get_user_id(request)
    game = get_imported_game_detail(game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return game


@router.post("/import/lichess", response_model=LichessImportResponse)
async def import_lichess_games(limit: int = Query(default=20, ge=10, le=20), request: Request = None) -> LichessImportResponse:
    user_id = _get_user_id(request)
    try:
        result = await import_latest_lichess_games(limit=limit, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LichessImportResponse(**result)


@router.post("/reprocess-all")
async def process_all_imported_games(request: Request) -> dict:
    user_id = _get_user_id(request)
    return reprocess_all_games(user_id)


@router.get("/{game_id}/share-card", response_model=ShareCardData)
async def imported_game_share_card(game_id: str, request: Request) -> ShareCardData:
    user_id = _get_user_id(request)
    card = get_share_card(game_id, user_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return ShareCardData.model_validate(card)


@router.get("/{game_id}/debug")
async def imported_game_debug(game_id: str, request: Request) -> dict:
    user_id = _get_user_id(request)
    debug = get_game_debug(game_id, user_id)
    if debug is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return debug


@router.post("/{game_id}/process")
async def process_imported_game(game_id: str, request: Request, with_eval: bool = Query(default=False)) -> dict:
    user_id = _get_user_id(request)
    game = reprocess_game(game_id, user_id, with_eval=with_eval)
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return game


@router.post("/{game_id}/analyze")
async def analyze_imported_game(game_id: str, request: Request) -> dict:
    user_id = _get_user_id(request)
    game = reprocess_game(game_id, user_id, with_eval=True)
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return game


@router.post("/{game_id}/debug-eval")
async def debug_eval_imported_game(game_id: str, payload: DebugEvalRequest, request: Request) -> dict:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="Not found")
    user_id = _get_user_id(request)
    game = debug_eval_game(
        game_id,
        user_id,
        [point.model_dump(mode="json") for point in payload.eval_curve],
        payload.analysis_status,
    )
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return game
