from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_session
from app.main import app
from app.models import Comment, Follow, Game, GameStory, Kudos, PublishedPost, User


def test_user_can_follow_and_unfollow_another_user() -> None:
    create_public_post("author", "author-post")
    client = TestClient(app)

    follow = client.post("/api/v1/profiles/author/follow", headers=session("viewer"))
    profile = client.get("/api/v1/profiles/author", headers=session("viewer"))
    unfollow = client.delete("/api/v1/profiles/author/follow", headers=session("viewer"))

    assert follow.status_code == 200
    assert follow.json()["following"] is True
    assert follow.json()["followers_count"] == 1
    assert profile.json()["viewer_is_following"] is True
    assert profile.json()["followers_count"] == 1
    assert unfollow.json()["following"] is False
    assert unfollow.json()["followers_count"] == 0


def test_user_cannot_follow_self() -> None:
    create_public_post("author", "author-post")
    client = TestClient(app)

    response = client.post("/api/v1/profiles/author/follow", headers=session("author"))

    assert response.status_code == 400
    assert "yourself" in response.json()["detail"]


def test_duplicate_follow_is_prevented() -> None:
    create_public_post("author", "author-post")
    client = TestClient(app)

    client.post("/api/v1/profiles/author/follow", headers=session("viewer"))
    client.post("/api/v1/profiles/author/follow", headers=session("viewer"))

    with get_session() as db:
        assert len(db.scalars(select(Follow)).all()) == 1


def test_feed_returns_posts_from_followed_users_only() -> None:
    followed_post = create_public_post("followed", "followed-post")
    create_public_post("stranger", "stranger-post")
    client = TestClient(app)
    client.post("/api/v1/profiles/followed/follow", headers=session("viewer"))

    response = client.get("/api/v1/feed", headers=session("viewer"))

    assert response.status_code == 200
    assert [post["id"] for post in response.json()["items"]] == [followed_post]
    assert response.json()["items"][0]["display_name"] == "followed"
    assert response.json()["items"][0]["game"]["final_fen"] == "8/8/8/8/8/8/8/8 w - - 0 1"


def test_feed_pagination_still_works() -> None:
    first_post = create_public_post("followed", "first-post")
    second_post = create_public_post("followed", "second-post")
    third_post = create_public_post("followed", "third-post")
    client = TestClient(app)
    client.post("/api/v1/profiles/followed/follow", headers=session("viewer"))

    first_page = client.get("/api/v1/feed?limit=2&offset=0", headers=session("viewer"))
    second_page = client.get("/api/v1/feed?limit=2&offset=2", headers=session("viewer"))

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["limit"] == 2
    assert len(first_page.json()["items"]) == 2
    assert [post["id"] for post in first_page.json()["items"]] == [third_post, second_post]
    assert [post["id"] for post in second_page.json()["items"]] == [first_post]


def test_feed_excludes_private_and_unpublished_posts() -> None:
    public_post = create_public_post("author", "public-post")
    create_public_post("author", "unpublished-post", visibility="unpublished")
    create_unpublished_journal_game("author")
    client = TestClient(app)
    client.post("/api/v1/profiles/author/follow", headers=session("viewer"))

    response = client.get("/api/v1/feed", headers=session("viewer"))

    assert [post["id"] for post in response.json()["items"]] == [public_post]


def test_kudos_can_be_added_without_duplicate_count() -> None:
    post_id = create_public_post("author", "author-post")
    client = TestClient(app)

    first = client.post(f"/api/v1/posts/{post_id}/kudos", headers=session("viewer"))
    second = client.post(f"/api/v1/posts/{post_id}/kudos", headers=session("viewer"))
    post = client.get(f"/api/v1/posts/{post_id}", headers=session("viewer"))

    assert first.status_code == 200
    assert second.json()["kudos_count"] == 1
    assert post.json()["kudos_count"] == 1
    assert post.json()["viewer_has_kudos"] is True
    with get_session() as db:
        assert len(db.scalars(select(Kudos)).all()) == 1


def test_kudos_can_be_removed() -> None:
    post_id = create_public_post("author", "author-post")
    client = TestClient(app)
    client.post(f"/api/v1/posts/{post_id}/kudos", headers=session("viewer"))

    response = client.delete(f"/api/v1/posts/{post_id}/kudos", headers=session("viewer"))

    assert response.status_code == 200
    assert response.json()["kudos_count"] == 0
    assert response.json()["viewer_has_kudos"] is False


def test_comments_can_be_added_to_public_post() -> None:
    post_id = create_public_post("author", "author-post")
    create_user("viewer")
    client = TestClient(app)

    response = client.post(f"/api/v1/posts/{post_id}/comments", headers=session("viewer"), json={"body": "Nice save"})
    comments = client.get(f"/api/v1/posts/{post_id}/comments")
    post = client.get(f"/api/v1/posts/{post_id}", headers=session("viewer"))

    assert response.status_code == 200
    assert response.json()["body"] == "Nice save"
    assert response.json()["author"]["display_name"] == "viewer"
    assert [comment["body"] for comment in comments.json()] == ["Nice save"]
    assert post.json()["comments_count"] == 1


def test_comments_cannot_be_empty() -> None:
    post_id = create_public_post("author", "author-post")
    client = TestClient(app)

    response = client.post(f"/api/v1/posts/{post_id}/comments", headers=session("viewer"), json={"body": "  "})

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_comments_and_kudos_only_work_on_public_posts() -> None:
    post_id = create_public_post("author", "author-post", visibility="unpublished")
    client = TestClient(app)

    kudos = client.post(f"/api/v1/posts/{post_id}/kudos", headers=session("viewer"))
    comment = client.post(f"/api/v1/posts/{post_id}/comments", headers=session("viewer"), json={"body": "Nope"})

    assert kudos.status_code == 404
    assert comment.status_code == 404
    with get_session() as db:
        assert len(db.scalars(select(Kudos)).all()) == 0
        assert len(db.scalars(select(Comment)).all()) == 0


def session(user_id: str) -> dict[str, str]:
    return {"X-Session-Id": user_id}


def create_user(username: str) -> None:
    with get_session() as db:
        if db.get(User, username) is None:
            db.add(User(id=username, username=username))


def create_public_post(username: str, external_id: str, *, visibility: str = "public") -> str:
    now = datetime.now(timezone.utc)
    with get_session() as db:
        user = db.get(User, username)
        if user is None:
            user = User(id=username, username=username, created_at=now, updated_at=now)
            db.add(user)
            db.flush()
        game = Game(
            user_id=user.id,
            chess_account_id=create_account_id(db, user.id),
            platform="lichess",
            external_game_id=external_id,
            pgn="[Event \"Test\"]\n\n1. e4 e5 1-0",
            raw_payload={},
            result="win",
            moves_count=1,
            final_fen="8/8/8/8/8/8/8/8 w - - 0 1",
            imported_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(game)
        db.flush()
        story = GameStory(
            game_id=game.id,
            user_id=user.id,
            primary_story="giant_slayer",
            badge_label="Giant Slayer",
            badge_emoji="GS",
            headline=f"{username} took down a stronger opponent.",
            template_key="giant_slayer_square_v1",
            interesting_score=0.85,
            confidence_score=0.9,
            reasons=["test"],
            share_card_data={},
            created_at=now,
            updated_at=now,
        )
        db.add(story)
        db.flush()
        post = PublishedPost(
            user_id=user.id,
            game_id=game.id,
            game_story_id=story.id,
            headline=story.headline,
            visibility=visibility,
            created_at=now,
            updated_at=now,
        )
        db.add(post)
        db.flush()
        return post.id


def create_unpublished_journal_game(username: str) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as db:
        user = db.get(User, username) or User(id=username, username=username)
        db.add(user)
        db.flush()
        db.add(
            Game(
                user_id=user.id,
                chess_account_id=create_account_id(db, user.id),
                platform="lichess",
                external_game_id="private-journal",
                pgn="[Event \"Private\"]\n\n1. e4 e5 1-0",
                raw_payload={},
                result="win",
                moves_count=1,
                imported_at=now,
                created_at=now,
                updated_at=now,
            )
        )


def create_account_id(db, user_id: str) -> str:
    from app.models import ChessAccount

    account = db.scalar(select(ChessAccount).where(ChessAccount.user_id == user_id, ChessAccount.platform == "lichess"))
    if account is None:
        account = ChessAccount(
            user_id=user_id,
            platform="lichess",
            platform_user_id=user_id,
            platform_username=user_id,
            access_token_encrypted="token",
            scopes=[],
        )
        db.add(account)
        db.flush()
    return account.id
