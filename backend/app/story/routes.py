from fastapi import APIRouter, HTTPException, Request

from app.games.repository import ignore_suggested_story, list_suggested_stories, reset_ignored_suggestions
from app.publishing.service import publish_story

router = APIRouter(prefix="/stories", tags=["stories"])


def _get_user_id(request: Request) -> str:
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.get("/suggested")
async def suggested_stories(request: Request) -> list[dict]:
    return list_suggested_stories(_get_user_id(request))


@router.post("/reset-ignored")
async def reset_ignored(request: Request) -> dict:
    return reset_ignored_suggestions(_get_user_id(request))


@router.post("/{story_id}/ignore")
async def ignore_story(story_id: str, request: Request) -> dict:
    result = ignore_suggested_story(story_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return result


@router.post("/{story_id}/publish")
async def publish_story_card(story_id: str, request: Request) -> dict:
    payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    card_theme = payload.get("card_theme") if isinstance(payload, dict) else None
    card_size = payload.get("card_size") if isinstance(payload, dict) else None
    result = publish_story(story_id, _get_user_id(request), card_theme=card_theme, card_size=card_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return result
