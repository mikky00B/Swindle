from fastapi import APIRouter, HTTPException, Request

from app.publishing.service import get_public_post, get_public_profile, list_profile_posts, unpublish_post

router = APIRouter(tags=["publishing"])


def _get_user_id(request: Request) -> str:
    return request.headers.get("X-Session-Id", "local-dev-user")


@router.post("/posts/{post_id}/unpublish")
async def unpublish_public_post(post_id: str, request: Request) -> dict:
    result = unpublish_post(post_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.get("/posts/{post_id}")
async def public_post(post_id: str) -> dict:
    result = get_public_post(post_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.get("/profiles/{username}")
async def public_profile(username: str) -> dict:
    result = get_public_profile(username)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/profiles/{username}/posts")
async def public_profile_posts(username: str) -> list[dict]:
    result = list_profile_posts(username)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result
