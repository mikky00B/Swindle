from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from app.auth.dependencies import require_user_id
from app.core.config import get_settings
from app.games.chesscom_import import import_latest_chesscom_games
from app.games.schemas import DebugEvalRequest
from app.games.lichess_import import import_latest_lichess_games
from app.games.repository import (
    debug_eval_game,
    get_game_debug,
    get_imported_game_detail,
    get_share_card,
    list_imported_games,
    queue_game_analysis,
    reprocess_all_games,
    reprocess_game,
    run_game_analysis_job,
)
from app.integrations.lichess.schemas import LichessImportResponse
from app.sessions.processor import rebuild_user_sessions
from app.share_cards.schemas import ShareCardData

router = APIRouter(prefix="/games", tags=["games"])


@router.get("")
async def games_journal(request: Request) -> list[dict]:
    user_id = require_user_id(request)
    return list_imported_games(user_id)


@router.get("/{game_id}")
async def game_detail(game_id: str, request: Request) -> dict:
    user_id = require_user_id(request)
    game = get_imported_game_detail(game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return game


@router.post("/import/lichess", response_model=LichessImportResponse)
async def import_lichess_games(request: Request, limit: int = Query(default=20, ge=10, le=20)) -> LichessImportResponse:
    user_id = require_user_id(request)
    try:
        result = await import_latest_lichess_games(limit=limit, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rebuild_user_sessions(user_id)
    return LichessImportResponse(**result)


@router.post("/import/chesscom", response_model=LichessImportResponse)
async def import_chesscom_games(request: Request, limit: int = Query(default=20, ge=1, le=20)) -> LichessImportResponse:
    user_id = require_user_id(request)
    try:
        result = await import_latest_chesscom_games(limit=limit, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rebuild_user_sessions(user_id)
    return LichessImportResponse(**result)


@router.post("/reprocess-all")
async def process_all_imported_games(request: Request) -> dict:
    user_id = require_user_id(request)
    result = reprocess_all_games(user_id)
    rebuild_user_sessions(user_id)
    return result


@router.get("/{game_id}/share-card", response_model=ShareCardData)
async def imported_game_share_card(game_id: str, request: Request) -> ShareCardData:
    user_id = require_user_id(request)
    card = get_share_card(game_id, user_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return ShareCardData.model_validate(card)


@router.get("/{game_id}/debug")
async def imported_game_debug(game_id: str, request: Request) -> dict:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="Not found")
    user_id = require_user_id(request)
    debug = get_game_debug(game_id, user_id)
    if debug is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    return debug


@router.post("/{game_id}/process")
async def process_imported_game(game_id: str, request: Request, with_eval: bool = Query(default=False)) -> dict:
    user_id = require_user_id(request)
    game = reprocess_game(game_id, user_id, with_eval=with_eval)
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    rebuild_user_sessions(user_id)
    return game


@router.post("/{game_id}/analyze")
async def analyze_imported_game(game_id: str, request: Request, background_tasks: BackgroundTasks) -> dict:
    """Queue cloud-eval analysis; it runs on a worker thread after this response."""
    user_id = require_user_id(request)
    if not queue_game_analysis(game_id, user_id):
        raise HTTPException(status_code=404, detail="Imported game not found")
    background_tasks.add_task(run_game_analysis_job, game_id, user_id)
    return {"queued": True, "game_id": game_id, "processing_status": "engine_processing"}


@router.post("/{game_id}/debug-eval")
async def debug_eval_imported_game(game_id: str, payload: DebugEvalRequest, request: Request) -> dict:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=404, detail="Not found")
    user_id = require_user_id(request)
    game = debug_eval_game(
        game_id,
        user_id,
        [point.model_dump(mode="json") for point in payload.eval_curve],
        payload.analysis_status,
    )
    if game is None:
        raise HTTPException(status_code=404, detail="Imported game not found")
    rebuild_user_sessions(user_id)
    return game
