from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.publishing.service import (
    SocialError,
    add_comment,
    add_kudos,
    delete_comment,
    follow_profile,
    get_public_post,
    get_public_profile,
    list_comments,
    list_feed,
    list_profile_followers,
    list_profile_following,
    list_profile_posts,
    remove_kudos,
    unfollow_profile,
    unpublish_post,
)

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
async def public_post(post_id: str, request: Request) -> dict:
    result = get_public_post(post_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.get("/profiles/{username}")
async def public_profile(username: str, request: Request) -> dict:
    result = get_public_profile(username, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/profiles/{username}/posts")
async def public_profile_posts(username: str) -> list[dict]:
    result = list_profile_posts(username)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.post("/profiles/{username}/follow")
async def follow_public_profile(username: str, request: Request) -> dict:
    try:
        result = follow_profile(username, _get_user_id(request))
    except SocialError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.delete("/profiles/{username}/follow")
async def unfollow_public_profile(username: str, request: Request) -> dict:
    result = unfollow_profile(username, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/profiles/{username}/followers")
async def public_profile_followers(username: str) -> list[dict]:
    result = list_profile_followers(username)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/profiles/{username}/following")
async def public_profile_following(username: str) -> list[dict]:
    result = list_profile_following(username)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/feed")
async def feed(request: Request, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0)) -> dict:
    return list_feed(_get_user_id(request), limit=limit, offset=offset)


@router.post("/posts/{post_id}/kudos")
async def give_kudos(post_id: str, request: Request) -> dict:
    result = add_kudos(post_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.delete("/posts/{post_id}/kudos")
async def delete_kudos(post_id: str, request: Request) -> dict:
    result = remove_kudos(post_id, _get_user_id(request))
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.get("/posts/{post_id}/comments")
async def public_post_comments(post_id: str) -> list[dict]:
    result = list_comments(post_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.post("/posts/{post_id}/comments")
async def create_public_post_comment(
    post_id: str,
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> dict:
    try:
        result = add_comment(post_id, _get_user_id(request), str(payload.get("body") or ""))
    except SocialError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.delete("/comments/{comment_id}")
async def remove_comment(comment_id: str, request: Request) -> dict:
    try:
        result = delete_comment(comment_id, _get_user_id(request))
    except SocialError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return result
