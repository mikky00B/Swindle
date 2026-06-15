from fastapi import APIRouter, HTTPException

from app.games.pgn_parser import parse_pgn
from app.games.schemas import PgnStoryRequest
from app.share_cards.schemas import ShareCardData, build_share_card_data
from app.story.processor import generate_story

router = APIRouter(prefix="/prototype", tags=["prototype"])


@router.post("/pgn-story", response_model=ShareCardData)
async def create_story_from_pgn(payload: PgnStoryRequest) -> ShareCardData:
    try:
        game = parse_pgn(payload.pgn, payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    story = generate_story(game, payload.metrics)
    return build_share_card_data(game, story, payload.metrics, payload.username)
