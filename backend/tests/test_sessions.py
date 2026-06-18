from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_session
from app.main import app
from app.models import ChessAccount, Game, GameSession, GameSessionGame, GameStory, User
from app.sessions.processor import rebuild_user_sessions


BASE_TIME = datetime(2026, 6, 18, 18, 0, tzinfo=timezone.utc)


def test_games_within_two_hours_group_into_one_session() -> None:
    create_games("player", [("win", 0), ("loss", 70), ("draw", 115)])

    result = rebuild_user_sessions("player")

    assert result == {"sessions": 1}
    with get_session() as db:
        recap = db.scalar(select(GameSession))
        assert recap is not None
        assert recap.games_count == 3


def test_gap_greater_than_two_hours_creates_new_session() -> None:
    create_games("player", [("win", 0), ("loss", 30), ("win", 190), ("draw", 220)])

    result = rebuild_user_sessions("player")

    assert result == {"sessions": 2}


def test_single_game_sessions_are_hidden_by_default() -> None:
    create_games("player", [("win", 0), ("loss", 190), ("draw", 380)])

    result = rebuild_user_sessions("player")

    assert result == {"sessions": 0}
    assert TestClient(app).get("/api/v1/sessions", headers=session("player")).json() == []


def test_session_counts_win_rate_opening_and_rating_delta_are_computed() -> None:
    create_games(
        "player",
        [
            ("win", 0, "Sicilian Defense", 12),
            ("loss", 20, "Sicilian Defense", -8),
            ("draw", 40, "French Defense", 0),
        ],
    )

    rebuild_user_sessions("player")

    recap = TestClient(app).get("/api/v1/sessions", headers=session("player")).json()[0]
    assert recap["wins_count"] == 1
    assert recap["losses_count"] == 1
    assert recap["draws_count"] == 1
    assert recap["win_rate"] == 1 / 3
    assert recap["most_common_opening"] == "Sicilian Defense"
    assert recap["rating_delta"] == 4


def test_clean_climb_mood_is_selected() -> None:
    create_games("player", [("win", 0), ("win", 10), ("win", 20), ("win", 30), ("loss", 40)])

    rebuild_user_sessions("player")

    recap = TestClient(app).get("/api/v1/sessions", headers=session("player")).json()[0]
    assert recap["mood"] == "Clean climb"


def test_tilt_session_mood_is_selected() -> None:
    create_games("player", [("loss", 0), ("loss", 10), ("loss", 20), ("loss", 30), ("win", 40)])

    rebuild_user_sessions("player")

    recap = TestClient(app).get("/api/v1/sessions", headers=session("player")).json()[0]
    assert recap["mood"] == "Tilt session"


def test_chaos_survived_mood_is_selected() -> None:
    create_games("player", [("win", 0, "Sicilian Defense", 5, "swindle"), ("loss", 10)])

    rebuild_user_sessions("player")

    recap = TestClient(app).get("/api/v1/sessions", headers=session("player")).json()[0]
    assert recap["mood"] == "Chaos survived"
    assert recap["swindle_count"] == 1


def test_best_story_selection_respects_priority_then_interest() -> None:
    create_games(
        "player",
        [
            ("win", 0, "Italian Game", 8, "miniature", 1.0),
            ("win", 10, "Italian Game", 8, "giant_slayer", 0.75),
            ("win", 20, "Italian Game", 8, "swindle", 0.7),
        ],
    )

    rebuild_user_sessions("player")

    recap = TestClient(app).get("/api/v1/sessions", headers=session("player")).json()[0]
    assert recap["best_story_type"] == "swindle"


def test_rebuild_sessions_is_idempotent() -> None:
    create_games("player", [("win", 0), ("loss", 10), ("draw", 20)])

    first = rebuild_user_sessions("player")
    second = rebuild_user_sessions("player")

    assert first == second == {"sessions": 1}
    with get_session() as db:
        assert len(db.scalars(select(GameSession)).all()) == 1
        assert len(db.scalars(select(GameSessionGame)).all()) == 3


def test_session_detail_endpoint_returns_games() -> None:
    create_games("player", [("win", 0), ("loss", 10)])
    rebuild_user_sessions("player")
    client = TestClient(app)
    session_id = client.get("/api/v1/sessions", headers=session("player")).json()[0]["id"]

    response = client.get(f"/api/v1/sessions/{session_id}", headers=session("player"))

    assert response.status_code == 200
    body = response.json()
    assert body["games_count"] == 2
    assert [game["result"] for game in body["games"]] == ["win", "loss"]
    assert body["share_card"]["kind"] == "session_recap"


def test_session_share_card_endpoint_returns_recap_card_data() -> None:
    create_games("player", [("win", 0), ("win", 10), ("loss", 20)])
    rebuild_user_sessions("player")
    client = TestClient(app)
    session_id = client.get("/api/v1/sessions", headers=session("player")).json()[0]["id"]

    response = client.get(f"/api/v1/sessions/{session_id}/share-card", headers=session("player"))

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "session_recap"
    assert body["session"]["games_count"] == 3
    assert body["stats"]["record"] == "2W - 1L - 0D"


def session(user_id: str) -> dict[str, str]:
    return {"X-Session-Id": user_id}


def create_games(
    username: str,
    specs: list[tuple[str, int] | tuple[str, int, str, int] | tuple[str, int, str, int, str] | tuple[str, int, str, int, str, float]],
) -> None:
    now = BASE_TIME
    with get_session() as db:
        user = db.get(User, username)
        if user is None:
            user = User(id=username, username=username, created_at=now, updated_at=now)
            db.add(user)
            db.flush()
        account = db.scalar(select(ChessAccount).where(ChessAccount.user_id == user.id, ChessAccount.platform == "lichess"))
        if account is None:
            account = ChessAccount(
                user_id=user.id,
                platform="lichess",
                platform_user_id=username,
                platform_username=username,
                access_token_encrypted="token",
                scopes=[],
                created_at=now,
                updated_at=now,
            )
            db.add(account)
            db.flush()
        for index, spec in enumerate(specs):
            result = spec[0]
            offset = spec[1]
            opening = spec[2] if len(spec) >= 3 else "Sicilian Defense"
            rating_change = spec[3] if len(spec) >= 4 else 0
            story_type = spec[4] if len(spec) >= 5 else ("giant_slayer" if result == "win" else "daily_activity")
            interest = spec[5] if len(spec) >= 6 else 0.8
            played_at = BASE_TIME + timedelta(minutes=offset)
            game = Game(
                user_id=user.id,
                chess_account_id=account.id,
                platform="lichess",
                external_game_id=f"{username}-{index}",
                pgn="[Event \"Session\"]\n\n1. e4 e5 1-0",
                raw_payload={},
                white_username=username,
                black_username=f"opp-{index}",
                user_color="white",
                opponent_username=f"opp-{index}",
                result=result,
                speed="blitz",
                time_control="5+0",
                opening_name=opening,
                moves_count=24 + index,
                rating_change=rating_change,
                played_at=played_at,
                imported_at=played_at,
                created_at=played_at,
                updated_at=played_at,
            )
            db.add(game)
            db.flush()
            story = GameStory(
                game_id=game.id,
                user_id=user.id,
                primary_story=story_type,
                badge_label=story_type.replace("_", " ").title(),
                badge_emoji="*",
                headline=f"{story_type} headline",
                template_key=f"{story_type}_square_v1",
                interesting_score=interest,
                confidence_score=0.8,
                reasons=["test"],
                share_card_data={},
                created_at=played_at,
                updated_at=played_at,
            )
            db.add(story)
