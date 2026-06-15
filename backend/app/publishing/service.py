from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.models import ChessAccount, Game, GameStory, PublishedPost, User


def publish_story(story_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        story = session.scalar(
            select(GameStory)
            .options(joinedload(GameStory.game).joinedload(Game.chess_account))
            .where(GameStory.id == story_id, GameStory.user_id == user_id)
        )
        if story is None:
            return None

        post = session.scalar(
            select(PublishedPost).where(
                PublishedPost.user_id == user_id,
                PublishedPost.game_story_id == story.id,
            )
        )
        now = datetime.now(timezone.utc)
        if post is None:
            post = PublishedPost(
                user_id=user_id,
                game_id=story.game_id,
                game_story_id=story.id,
                headline=story.headline,
                caption=story.caption,
                visibility="public",
                created_at=now,
                updated_at=now,
            )
            session.add(post)
            session.flush()
        else:
            post.headline = story.headline
            post.caption = story.caption
            post.visibility = "public"
            post.updated_at = now
            session.flush()

        return _post_to_dict(session, post)


def unpublish_post(post_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        post = session.scalar(select(PublishedPost).where(PublishedPost.id == post_id, PublishedPost.user_id == user_id))
        if post is None:
            return None
        post.visibility = "unpublished"
        post.updated_at = datetime.now(timezone.utc)
        session.flush()
        return {"id": post.id, "visibility": post.visibility, "unpublished": True}


def get_public_profile(username: str) -> dict[str, Any] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        posts = _public_posts_for_user(session, user.id)
        lichess_username = _connected_lichess_username(session, user.id)
        display_name = _public_display_name(user, lichess_username)
        return {
            "display_name": display_name,
            "profile_slug": _profile_slug(display_name),
            "lichess_username": lichess_username,
            "published_cards_count": len(posts),
            "wins_shown": sum(1 for post in posts if post.game and post.game.result == "win"),
            "losses_shown": sum(1 for post in posts if post.game and post.game.result == "loss"),
            "common_story": _most_common_story_type(posts),
            "games_imported": session.scalar(select(func.count()).select_from(Game).where(Game.user_id == user.id)) or 0,
            "posts": [_post_to_dict(session, post, include_share_card=False) for post in posts],
        }


def list_profile_posts(username: str) -> list[dict[str, Any]] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        return [_post_to_dict(session, post, include_share_card=False) for post in _public_posts_for_user(session, user.id)]


def get_public_post(post_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        post = session.scalar(
            select(PublishedPost)
            .options(
                joinedload(PublishedPost.game),
                joinedload(PublishedPost.game_story),
            )
            .where(PublishedPost.id == post_id, PublishedPost.visibility == "public")
        )
        if post is None:
            return None
        return _post_to_dict(session, post, include_share_card=True)


def _get_profile_user(session, username: str) -> User | None:
    lowered = username.lower()
    user = session.scalar(
        select(User).where(
            func.lower(User.username) == lowered,
            ~User.username.startswith("local"),
        )
    )
    if user is not None:
        return user
    accounts = (
        session.scalars(
            select(ChessAccount)
            .options(joinedload(ChessAccount.user))
            .where(ChessAccount.platform == "lichess", func.lower(ChessAccount.platform_username) == lowered)
        )
        .unique()
        .all()
    )
    if not accounts:
        return None
    for account in accounts:
        has_public_post = session.scalar(
            select(PublishedPost.id)
            .where(PublishedPost.user_id == account.user_id, PublishedPost.visibility == "public")
            .limit(1)
        )
        if has_public_post:
            return account.user
    return accounts[0].user


def _public_posts_for_user(session, user_id: str) -> list[PublishedPost]:
    return (
        session.scalars(
            select(PublishedPost)
            .options(
                joinedload(PublishedPost.game),
                joinedload(PublishedPost.game_story),
            )
            .where(PublishedPost.user_id == user_id, PublishedPost.visibility == "public")
            .order_by(PublishedPost.created_at.desc())
        )
        .unique()
        .all()
    )


def _connected_lichess_username(session, user_id: str) -> str | None:
    return session.scalar(
        select(ChessAccount.platform_username).where(ChessAccount.user_id == user_id, ChessAccount.platform == "lichess")
    )


def _most_common_story_type(posts: list[PublishedPost]) -> str | None:
    stories = [post.game_story.primary_story for post in posts if post.game_story is not None]
    if not stories:
        return None
    return Counter(stories).most_common(1)[0][0]


def _post_to_dict(session, post: PublishedPost, *, include_share_card: bool = True) -> dict[str, Any]:
    game = post.game or session.get(Game, post.game_id)
    story = post.game_story or session.get(GameStory, post.game_story_id)
    lichess_username = _connected_lichess_username(session, post.user_id)
    user = session.get(User, post.user_id)
    display_name = _public_display_name(user, lichess_username)
    payload: dict[str, Any] = {
        "id": post.id,
        "game_id": post.game_id,
        "game_story_id": post.game_story_id,
        "headline": post.headline,
        "caption": post.caption,
        "visibility": post.visibility,
        "created_at": _iso(post.created_at),
        "updated_at": _iso(post.updated_at),
        "display_name": display_name,
        "profile_slug": _profile_slug(display_name),
        "lichess_username": lichess_username,
        "game": _game_summary(game),
        "story": _story_summary(story),
    }
    if include_share_card and story is not None:
        payload["share_card"] = story.share_card_data
    return payload


def _game_summary(game: Game | None) -> dict[str, Any] | None:
    if game is None:
        return None
    return {
        "id": game.id,
        "external_game_id": game.external_game_id,
        "platform": game.platform,
        "result": game.result,
        "opening_name": game.opening_name,
        "opponent_username": game.opponent_username,
        "moves_count": game.moves_count,
        "speed": game.speed,
        "time_control": game.time_control,
        "played_at": _iso(game.played_at),
    }


def _story_summary(story: GameStory | None) -> dict[str, Any] | None:
    if story is None:
        return None
    return {
        "id": story.id,
        "primary_story": story.primary_story,
        "badge_label": story.badge_label,
        "badge_emoji": story.badge_emoji,
        "headline": story.headline,
        "interesting_score": story.interesting_score,
        "key_position_fen": story.key_position_fen,
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _public_display_name(user: User | None, lichess_username: str | None) -> str:
    if user is not None and user.username and not _is_internal_username(user.username):
        return user.username
    if lichess_username:
        return lichess_username
    return "Player"


def _profile_slug(display_name: str) -> str:
    return display_name or "Player"


def _is_internal_username(username: str) -> bool:
    lowered = username.lower()
    return lowered == "local" or lowered.startswith("local-") or lowered.startswith("session-")
