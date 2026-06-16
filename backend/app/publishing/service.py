from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.integrations.lichess.service import ensure_local_user
from app.models import ChessAccount, Comment, Follow, Game, GameMetric, GameStory, Kudos, PublishedPost, User


class SocialError(ValueError):
    pass


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


def get_public_profile(username: str, viewer_user_id: str | None = None) -> dict[str, Any] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        posts = _public_posts_for_user(session, user.id)
        lichess_username = _connected_lichess_username(session, user.id)
        display_name = _public_display_name(user, lichess_username)
        followers_count = _followers_count(session, user.id)
        following_count = _following_count(session, user.id)
        viewer_is_self = viewer_user_id == user.id
        viewer_is_following = bool(viewer_user_id and _follow_exists(session, viewer_user_id, user.id))
        return {
            "display_name": display_name,
            "profile_slug": _profile_slug(display_name),
            "lichess_username": lichess_username,
            "published_cards_count": len(posts),
            "followers_count": followers_count,
            "following_count": following_count,
            "viewer_is_self": viewer_is_self,
            "viewer_is_following": viewer_is_following,
            "wins_shown": sum(1 for post in posts if post.game and post.game.result == "win"),
            "losses_shown": sum(1 for post in posts if post.game and post.game.result == "loss"),
            "common_story": _most_common_story_type(posts),
            "games_imported": session.scalar(select(func.count()).select_from(Game).where(Game.user_id == user.id)) or 0,
            "posts": [_post_to_dict(session, post, include_share_card=False, viewer_user_id=viewer_user_id) for post in posts],
        }


def list_profile_posts(username: str) -> list[dict[str, Any]] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        return [_post_to_dict(session, post, include_share_card=False) for post in _public_posts_for_user(session, user.id)]


def get_public_post(post_id: str, viewer_user_id: str | None = None) -> dict[str, Any] | None:
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
        return _post_to_dict(session, post, include_share_card=True, viewer_user_id=viewer_user_id)


def follow_profile(username: str, follower_user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        follower = ensure_local_user(session, follower_user_id)
        following = _get_profile_user(session, username)
        if following is None:
            return None
        if follower.id == following.id:
            raise SocialError("You cannot follow yourself")
        existing = session.scalar(
            select(Follow).where(Follow.follower_id == follower.id, Follow.following_id == following.id)
        )
        if existing is None:
            session.add(Follow(follower_id=follower.id, following_id=following.id))
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
        return _follow_summary(session, following.id, follower.id)


def unfollow_profile(username: str, follower_user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        following = _get_profile_user(session, username)
        if following is None:
            return None
        existing = session.scalar(
            select(Follow).where(Follow.follower_id == follower_user_id, Follow.following_id == following.id)
        )
        if existing is not None:
            session.delete(existing)
            session.flush()
        return _follow_summary(session, following.id, follower_user_id)


def list_profile_followers(username: str) -> list[dict[str, Any]] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        follows = session.scalars(select(Follow).where(Follow.following_id == user.id).order_by(Follow.created_at.desc())).all()
        return [_user_summary(session, follow.follower_id) for follow in follows]


def list_profile_following(username: str) -> list[dict[str, Any]] | None:
    with get_session() as session:
        user = _get_profile_user(session, username)
        if user is None:
            return None
        follows = session.scalars(select(Follow).where(Follow.follower_id == user.id).order_by(Follow.created_at.desc())).all()
        return [_user_summary(session, follow.following_id) for follow in follows]


def list_feed(user_id: str, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    with get_session() as session:
        ensure_local_user(session, user_id)
        following_ids = select(Follow.following_id).where(Follow.follower_id == user_id)
        total = (
            session.scalar(
                select(func.count())
                .select_from(PublishedPost)
                .where(PublishedPost.user_id.in_(following_ids), PublishedPost.visibility == "public")
            )
            or 0
        )
        posts = (
            session.scalars(
                select(PublishedPost)
                .options(
                    joinedload(PublishedPost.game).joinedload(Game.metrics),
                    joinedload(PublishedPost.game_story),
                )
                .where(PublishedPost.user_id.in_(following_ids), PublishedPost.visibility == "public")
                .order_by(PublishedPost.created_at.desc())
                .offset(max(offset, 0))
                .limit(min(max(limit, 1), 50))
            )
            .unique()
            .all()
        )
        return {
            "items": [_post_to_dict(session, post, include_share_card=False, viewer_user_id=user_id) for post in posts],
            "limit": limit,
            "offset": offset,
            "total": total,
        }


def add_kudos(post_id: str, user_id: str, reaction_type: str = "kudos") -> dict[str, Any] | None:
    with get_session() as session:
        ensure_local_user(session, user_id)
        post = _public_post(session, post_id)
        if post is None:
            return None
        existing = session.scalar(
            select(Kudos).where(Kudos.post_id == post_id, Kudos.user_id == user_id, Kudos.type == reaction_type)
        )
        if existing is None:
            session.add(Kudos(post_id=post_id, user_id=user_id, type=reaction_type))
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
        return _post_social_counts(session, post_id, user_id)


def remove_kudos(post_id: str, user_id: str, reaction_type: str = "kudos") -> dict[str, Any] | None:
    with get_session() as session:
        post = _public_post(session, post_id)
        if post is None:
            return None
        existing = session.scalar(
            select(Kudos).where(Kudos.post_id == post_id, Kudos.user_id == user_id, Kudos.type == reaction_type)
        )
        if existing is not None:
            session.delete(existing)
            session.flush()
        return _post_social_counts(session, post_id, user_id)


def list_comments(post_id: str) -> list[dict[str, Any]] | None:
    with get_session() as session:
        if _public_post(session, post_id) is None:
            return None
        comments = (
            session.scalars(
                select(Comment)
                .where(Comment.post_id == post_id, Comment.deleted_at.is_(None))
                .order_by(Comment.created_at.asc())
            )
            .all()
        )
        return [_comment_to_dict(session, comment) for comment in comments]


def add_comment(post_id: str, user_id: str, body: str) -> dict[str, Any] | None:
    cleaned = body.strip()
    if not cleaned:
        raise SocialError("Comment cannot be empty")
    with get_session() as session:
        ensure_local_user(session, user_id)
        if _public_post(session, post_id) is None:
            return None
        comment = Comment(post_id=post_id, user_id=user_id, body=cleaned)
        session.add(comment)
        session.flush()
        return _comment_to_dict(session, comment)


def delete_comment(comment_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        comment = session.get(Comment, comment_id)
        if comment is None or comment.deleted_at is not None:
            return None
        if _public_post(session, comment.post_id) is None:
            return None
        if comment.user_id != user_id:
            raise SocialError("You can only delete your own comments")
        comment.deleted_at = datetime.now(timezone.utc)
        comment.updated_at = comment.deleted_at
        session.flush()
        return {"id": comment.id, "deleted": True}


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


def _post_to_dict(
    session,
    post: PublishedPost,
    *,
    include_share_card: bool = True,
    viewer_user_id: str | None = None,
) -> dict[str, Any]:
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
        "metrics": _metrics_summary(game.metrics if game is not None else None),
        **_post_social_counts(session, post.id, viewer_user_id),
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


def _metrics_summary(metrics: GameMetric | None) -> dict[str, Any] | None:
    if metrics is None:
        return None
    return {
        "accuracy": metrics.accuracy,
        "lowest_eval": metrics.lowest_eval,
        "highest_eval": metrics.highest_eval,
        "biggest_eval_swing": metrics.biggest_eval_swing,
        "turning_point_move": metrics.turning_point_move,
        "analysis_source": metrics.analysis_source,
        "analysis_status": metrics.analysis_status,
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


def _public_post(session, post_id: str) -> PublishedPost | None:
    return session.scalar(select(PublishedPost).where(PublishedPost.id == post_id, PublishedPost.visibility == "public"))


def _followers_count(session, user_id: str) -> int:
    return session.scalar(select(func.count()).select_from(Follow).where(Follow.following_id == user_id)) or 0


def _following_count(session, user_id: str) -> int:
    return session.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)) or 0


def _follow_exists(session, follower_id: str, following_id: str) -> bool:
    return bool(session.scalar(select(Follow.id).where(Follow.follower_id == follower_id, Follow.following_id == following_id)))


def _follow_summary(session, following_id: str, follower_id: str) -> dict[str, Any]:
    return {
        "following": _follow_exists(session, follower_id, following_id),
        "followers_count": _followers_count(session, following_id),
        "following_count": _following_count(session, following_id),
    }


def _post_social_counts(session, post_id: str, viewer_user_id: str | None = None) -> dict[str, Any]:
    kudos_count = (
        session.scalar(select(func.count()).select_from(Kudos).where(Kudos.post_id == post_id, Kudos.type == "kudos"))
        or 0
    )
    comments_count = (
        session.scalar(
            select(func.count()).select_from(Comment).where(Comment.post_id == post_id, Comment.deleted_at.is_(None))
        )
        or 0
    )
    viewer_has_kudos = bool(
        viewer_user_id
        and session.scalar(
            select(Kudos.id).where(Kudos.post_id == post_id, Kudos.user_id == viewer_user_id, Kudos.type == "kudos")
        )
    )
    return {
        "kudos_count": kudos_count,
        "comments_count": comments_count,
        "viewer_has_kudos": viewer_has_kudos,
    }


def _comment_to_dict(session, comment: Comment) -> dict[str, Any]:
    author = _user_summary(session, comment.user_id)
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "body": comment.body,
        "created_at": _iso(comment.created_at),
        "author": author,
    }


def _user_summary(session, user_id: str) -> dict[str, Any]:
    user = session.get(User, user_id)
    lichess_username = _connected_lichess_username(session, user_id)
    display_name = _public_display_name(user, lichess_username)
    return {
        "display_name": display_name,
        "profile_slug": _profile_slug(display_name),
        "lichess_username": lichess_username,
    }
