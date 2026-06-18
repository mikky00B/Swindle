from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.games import analysis
from app.core.database import get_session
from app.main import app
from app.models import Game, GameStory, OAuthState, PublishedPost, SuggestedPost, User
from app.integrations.lichess.service import ensure_local_user, lichess_api_url
from tests.test_prototype_api import SAMPLE_PGN


class MockAsyncClient:
    payloads: list[dict[str, Any]] | None = None
    status_code: int = 200
    account_status_code: int = 200

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        assert kwargs["data"]["code"] == "oauth-code"
        assert kwargs["data"]["code_verifier"]
        return httpx.Response(
            200,
            json={"access_token": "lichess-access-token", "scope": "email:read", "token_type": "Bearer"},
            request=httpx.Request("POST", url),
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        assert kwargs["headers"]["Authorization"] == "Bearer lichess-access-token"
        if url.endswith("/api/account"):
            if self.account_status_code != 200:
                return httpx.Response(self.account_status_code, text="bad account", request=httpx.Request("GET", url))
            return httpx.Response(200, json={"id": "clevermike", "username": "clevermike"}, request=httpx.Request("GET", url))
        if self.status_code != 200:
            return httpx.Response(self.status_code, text="error", request=httpx.Request("GET", url))
        payloads = self.payloads if self.payloads is not None else [base_payload("game-one")]
        return httpx.Response(
            200,
            text="".join(json.dumps(payload) + "\n" for payload in payloads),
            request=httpx.Request("GET", url),
        )


def test_oauth_callback_stores_connected_account(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = TestClient(app)

    connect = client.get("/api/v1/integrations/lichess/connect", follow_redirects=False)
    assert connect.status_code == 302
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))

    callback = client.get(
        f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 302
    status = client.get("/api/v1/integrations/lichess/status")
    assert status.json()["connected"] is True
    assert status.json()["platform_username"] == "clevermike"


def test_connect_url_endpoint_returns_oauth_url_for_session_user() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/integrations/lichess/connect-url",
        headers={"X-Session-Id": "session-1781471651808-46122pw6o"},
    )

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://lichess.org/oauth?")
    with get_session() as session:
        user = session.get(User, "session-1781471651808-46122pw6o")
        state = session.scalar(select(OAuthState))
    assert user is not None
    assert user.username == "local-session-1781471651808-46122pw6o"
    assert state is not None
    assert state.user_id == user.id


def test_connect_redirect_accepts_session_id_query_param() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/integrations/lichess/connect?session_id=session-1781471651808-46122pw6o",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://lichess.org/oauth?")
    with get_session() as session:
        user = session.get(User, "session-1781471651808-46122pw6o")
        state = session.scalar(select(OAuthState))
    assert user is not None
    assert state is not None
    assert state.user_id == user.id


def test_local_session_users_get_unique_placeholder_usernames() -> None:
    with get_session() as session:
        first = ensure_local_user(session, "session-1781471651808-46122pw6o")
        second = ensure_local_user(session, "session-1781471651808-otheruser")

    assert first.username == "local-session-1781471651808-46122pw6o"
    assert second.username == "local-session-1781471651808-otheruser"
    with get_session() as session:
        assert len(session.scalars(select(User)).all()) == 2


def test_lichess_api_url_accepts_root_or_api_base(monkeypatch) -> None:
    monkeypatch.setenv("LICHESS_API_BASE_URL", "https://lichess.org")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert lichess_api_url("/account") == "https://lichess.org/api/account"

    monkeypatch.setenv("LICHESS_API_BASE_URL", "https://lichess.org/api")
    get_settings.cache_clear()
    assert lichess_api_url("/account") == "https://lichess.org/api/account"


def test_invalid_oauth_state_is_rejected() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/integrations/lichess/callback?code=oauth-code&state=bad", follow_redirects=False)

    assert response.status_code == 302
    assert "lichess=error" in response.headers["location"]


def test_callback_redirects_with_error_when_account_lookup_fails(monkeypatch) -> None:
    MockAsyncClient.account_status_code = 404
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = TestClient(app)
    client.get("/api/v1/integrations/lichess/connect", follow_redirects=False)
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))

    response = client.get(
        f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "lichess=error" in response.headers["location"]
    MockAsyncClient.account_status_code = 200


def test_disconnect_removes_connected_account(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = TestClient(app)
    connect = client.get("/api/v1/integrations/lichess/connect", follow_redirects=False)
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))
    client.get(f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}", follow_redirects=False)

    response = client.post("/api/v1/integrations/lichess/disconnect")

    assert response.status_code == 200
    assert response.json()["disconnected"] is True
    assert client.get("/api/v1/integrations/lichess/status").json()["connected"] is False


def test_import_latest_games_deduplicates_and_generates_share_card(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = TestClient(app)
    connect = client.get("/api/v1/integrations/lichess/connect", follow_redirects=False)
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))
    client.get(f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}", follow_redirects=False)

    first = client.post("/api/v1/games/import/lichess")
    second = client.post("/api/v1/games/import/lichess")
    journal = client.get("/api/v1/games")

    assert first.status_code == 200
    assert first.json() == {"imported": 1, "duplicates": 0, "skipped": 0, "total_seen": 1, "errors": []}
    assert second.json() == {"imported": 0, "duplicates": 1, "skipped": 0, "total_seen": 1, "errors": []}
    assert len(journal.json()) == 1
    game_id = journal.json()[0]["id"]

    card = client.get(f"/api/v1/games/{game_id}/share-card")
    assert card.status_code == 200
    assert card.json()["player"]["username"] == "clevermike"
    assert card.json()["game"]["moves"] == 31
    assert card.json()["game"]["user_color"] == "white"
    assert card.json()["game"]["opponent_username"] == "higherRated"
    assert card.json()["game"]["final_fen"]
    assert card.json()["board_position_source"] == "final_position"
    assert card.json()["story"]["key_position_fen"]

    debug = client.get(f"/api/v1/games/{game_id}/debug")
    assert debug.status_code == 200
    assert debug.json()["final_fen"] == card.json()["game"]["final_fen"]
    assert debug.json()["card_fen"] == card.json()["story"]["key_position_fen"]


def test_giant_slayer_import_creates_suggested_story(monkeypatch) -> None:
    MockAsyncClient.payloads = [base_payload("giant-slayer")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    client.post("/api/v1/games/import/lichess")
    suggestions = client.get("/api/v1/stories/suggested")

    assert suggestions.status_code == 200
    assert len(suggestions.json()) == 1
    assert suggestions.json()[0]["story"]["primary_story"] == "giant_slayer"
    assert suggestions.json()[0]["story"]["interesting_score"] >= 0.75
    MockAsyncClient.payloads = None


def test_miniature_import_creates_suggested_story(monkeypatch) -> None:
    MockAsyncClient.payloads = [moves_payload("miniature", moves="e4 e5 Qh5 Nc6 Bc4 Nf6 Qxf7#")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    client.post("/api/v1/games/import/lichess")
    suggestion = client.get("/api/v1/stories/suggested").json()[0]

    assert suggestion["story"]["primary_story"] == "miniature"
    assert suggestion["moves_count"] == 4
    MockAsyncClient.payloads = None


def test_long_grind_import_creates_suggested_story_when_threshold_is_met(monkeypatch) -> None:
    MockAsyncClient.payloads = [moves_payload("long-grind", moves=repetition_moves(35), winner=None)]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    client.post("/api/v1/games/import/lichess")
    suggestion = client.get("/api/v1/stories/suggested").json()[0]

    assert suggestion["story"]["primary_story"] == "long_grind"
    assert suggestion["story"]["interesting_score"] >= 0.70
    assert suggestion["moves_count"] == 70
    MockAsyncClient.payloads = None


def test_daily_game_does_not_create_suggested_story_by_default(monkeypatch) -> None:
    MockAsyncClient.payloads = [moves_payload("daily", moves=repetition_moves(19), winner=None)]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    client.post("/api/v1/games/import/lichess")
    suggestions = client.get("/api/v1/stories/suggested")

    assert suggestions.json() == []
    with get_session() as session:
        assert len(session.scalars(select(SuggestedPost)).all()) == 0
    MockAsyncClient.payloads = None


def test_ignored_suggestion_disappears_but_game_stays_in_journal(monkeypatch) -> None:
    MockAsyncClient.payloads = [base_payload("ignored-giant")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    suggestion = client.get("/api/v1/stories/suggested").json()[0]

    response = client.post(f"/api/v1/stories/{suggestion['story']['id']}/ignore")

    assert response.status_code == 200
    assert client.get("/api/v1/stories/suggested").json() == []
    journal = client.get("/api/v1/games").json()
    assert len(journal) == 1
    assert journal[0]["external_game_id"] == "ignored-giant"
    MockAsyncClient.payloads = None


def test_reset_ignored_suggestions_restores_suggested_items(monkeypatch) -> None:
    MockAsyncClient.payloads = [base_payload("reset-giant")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    suggestion = client.get("/api/v1/stories/suggested").json()[0]
    client.post(f"/api/v1/stories/{suggestion['story']['id']}/ignore")

    response = client.post("/api/v1/stories/reset-ignored")

    assert response.status_code == 200
    assert response.json()["restored"] == 1
    assert len(client.get("/api/v1/stories/suggested").json()) == 1
    MockAsyncClient.payloads = None


def test_import_latest_games_uses_session_user_id(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    session_headers = {"X-Session-Id": "session-import-user"}
    client = TestClient(app)
    client.get("/api/v1/integrations/lichess/connect-url", headers=session_headers)
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))
    client.get(f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}", follow_redirects=False)

    response = client.post("/api/v1/games/import/lichess", headers=session_headers)
    journal = client.get("/api/v1/games", headers=session_headers)
    default_journal = client.get("/api/v1/games")

    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert len(journal.json()) == 1
    assert default_journal.json() == []


def test_import_handles_missing_fields_without_failing(monkeypatch) -> None:
    MockAsyncClient.payloads = [
        base_payload(
            "ok-no-opening",
            opening=None,
            players={"white": {"user": {"name": "clevermike"}}, "black": {}},
            pgn=SAMPLE_PGN.replace('[Opening "Sicilian Defense"]\n', "")
            .replace('[WhiteElo "1392"]\n', "")
            .replace('[BlackElo "1560"]\n', ""),
        ),
        {"id": "missing-pgn"},
    ]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    response = client.post("/api/v1/games/import/lichess")
    journal = client.get("/api/v1/games")

    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert response.json()["skipped"] == 1
    assert journal.json()[0]["opening_name"] is None
    assert journal.json()[0]["opponent_rating"] is None
    MockAsyncClient.payloads = None


def test_import_replays_lichess_moves_when_pgn_is_missing(monkeypatch) -> None:
    MockAsyncClient.payloads = [
        {
            "id": "moves-only",
            "moves": "e4 e5 Nf3 Nc6 Bb5 a6",
            "winner": "white",
            "status": "mate",
            "rated": True,
            "speed": "blitz",
            "clock": {"initial": 300, "increment": 0},
            "createdAt": 1781432100000,
            "opening": {"eco": "C60", "name": "Ruy Lopez"},
            "players": {
                "white": {"user": {"name": "clevermike"}, "rating": 1392, "ratingDiff": 8},
                "black": {"user": {"name": "Bai_Daniil"}, "rating": 1096, "ratingDiff": -8},
            },
        }
    ]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    response = client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()
    debug = client.get(f"/api/v1/games/{game['id']}/debug").json()

    assert response.json()["imported"] == 1
    assert game["moves_count"] == 3
    assert game["final_fen"] == "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"
    assert card["game"]["final_fen"] == game["final_fen"]
    assert card["story"]["key_position_fen"] == game["final_fen"]
    assert card["board_position_source"] == "final_position"
    assert debug["card_fen"] == game["final_fen"]
    MockAsyncClient.payloads = None


def test_reprocess_backfills_missing_final_fen_from_raw_moves(monkeypatch) -> None:
    MockAsyncClient.payloads = [
        {
            "id": "stale-moves-only",
            "moves": "e4 e5 Nf3 Nc6 Bb5 a6",
            "winner": "white",
            "speed": "blitz",
            "players": {
                "white": {"user": {"name": "clevermike"}, "rating": 1392},
                "black": {"user": {"name": "Bai_Daniil"}, "rating": 1096},
            },
        }
    ]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game_id = client.get("/api/v1/games").json()[0]["id"]
    with get_session() as session:
        game = session.get(Game, game_id)
        game.final_fen = None
        game.story.key_position_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        game.story.share_card_data = {
            **game.story.share_card_data,
            "board_position_source": "fallback_starting_position",
            "game": {**game.story.share_card_data["game"], "final_fen": None},
        }

    response = client.post(f"/api/v1/games/{game_id}/process")
    card = client.get(f"/api/v1/games/{game_id}/share-card").json()

    assert response.status_code == 200
    assert response.json()["final_fen"] == "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"
    assert card["story"]["key_position_fen"] == response.json()["final_fen"]
    assert card["board_position_source"] == "final_position"
    MockAsyncClient.payloads = None


def test_import_private_account_error_is_clear(monkeypatch) -> None:
    MockAsyncClient.status_code = 403
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    response = client.post("/api/v1/games/import/lichess")

    assert response.status_code == 400
    assert "private" in response.json()["detail"]
    MockAsyncClient.status_code = 200


def test_empty_game_import_is_successful(monkeypatch) -> None:
    MockAsyncClient.payloads = []
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    response = client.post("/api/v1/games/import/lichess")

    assert response.status_code == 200
    assert response.json() == {"imported": 0, "duplicates": 0, "skipped": 0, "total_seen": 0, "errors": []}
    MockAsyncClient.payloads = None


def test_reprocess_game_updates_existing_story(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game_id = client.get("/api/v1/games").json()[0]["id"]

    response = client.post(f"/api/v1/games/{game_id}/process")

    assert response.status_code == 200
    assert response.json()["processing_status"] == "processed"
    with get_session() as session:
        assert len(session.scalars(select(GameStory)).all()) == 1
        assert len(session.scalars(select(Game)).all()) == 1


def test_analyze_updates_daily_game_into_swindle_with_key_position(monkeypatch) -> None:
    payload = base_payload(
        "eval-swindle",
        players={
            "white": {"user": {"name": "clevermike"}, "rating": 1392, "ratingDiff": 14},
            "black": {"user": {"name": "nearPeer"}, "rating": 1400, "ratingDiff": -14},
        },
    )
    MockAsyncClient.payloads = [payload]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    evals = iter([-20, -520, -450, 120, 240, 320])

    def fake_cloud_eval(fen: str) -> dict:
        return {"cp": next(evals, 300), "mate": None, "depth": 21}

    monkeypatch.setattr(analysis, "fetch_cloud_eval", fake_cloud_eval)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]
    assert game["story"]["primary_story"] == "daily_activity"

    response = client.post(f"/api/v1/games/{game['id']}/analyze")
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()

    assert response.status_code == 200
    assert response.json()["story"]["primary_story"] == "swindle"
    assert response.json()["story"]["key_position_fen"]
    assert card["story"]["primary_story"] == "swindle"
    assert card["board_position_source"] == "key_position"
    assert card["metrics"]["lowest_eval"] <= -5.0
    assert card["metrics"]["analysis_status"] in {"partial", "complete"}
    assert card["metrics"]["eval_points"] >= 2
    assert response.json()["metrics"]["eval_points"] >= 2
    assert response.json()["metrics"]["analysis_source"] == "lichess_cloud_eval"
    MockAsyncClient.payloads = None


def test_analyze_updates_daily_game_into_heartbreaker(monkeypatch) -> None:
    payload = base_payload(
        "eval-heartbreaker",
        players={
            "white": {"user": {"name": "clevermike"}, "rating": 1392, "ratingDiff": -10},
            "black": {"user": {"name": "nearPeer"}, "rating": 1400, "ratingDiff": 10},
        },
        pgn=SAMPLE_PGN.replace('[Result "1-0"]', '[Result "0-1"]').replace("31. Be6 1-0", "31. Be6 0-1"),
    )
    MockAsyncClient.payloads = [payload]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    evals = iter([20, 520, 500, 120, -120, -240])

    def fake_cloud_eval(fen: str) -> dict:
        return {"cp": next(evals, -250), "mate": None, "depth": 21}

    monkeypatch.setattr(analysis, "fetch_cloud_eval", fake_cloud_eval)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]

    response = client.post(f"/api/v1/games/{game['id']}/analyze")
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()

    assert response.status_code == 200
    assert response.json()["story"]["primary_story"] == "heartbreaker"
    assert card["story"]["primary_story"] == "heartbreaker"
    assert card["board_position_source"] == "key_position"
    assert card["metrics"]["highest_eval"] >= 5.0
    MockAsyncClient.payloads = None


def test_debug_eval_updates_card_into_swindle(monkeypatch) -> None:
    MockAsyncClient.payloads = [quiet_payload("debug-swindle", winner="white")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]

    response = client.post(
        f"/api/v1/games/{game['id']}/debug-eval",
        json={"eval_curve": [{"eval": 0.2}, {"eval": -5.2}, {"eval": 1.4}], "analysis_status": "complete"},
    )
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()

    assert response.status_code == 200
    assert response.json()["story"]["primary_story"] == "swindle"
    assert response.json()["story"]["interesting_score"] >= 0.75
    assert card["story"]["badge_label"] == "The Swindle"
    assert card["story"]["headline"] == "Completely lost, somehow walked out with the full point."
    assert card["board_position_source"] == "key_position"
    MockAsyncClient.payloads = None


def test_debug_eval_updates_card_into_heartbreaker(monkeypatch) -> None:
    MockAsyncClient.payloads = [quiet_payload("debug-heartbreaker", winner="black")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]

    response = client.post(
        f"/api/v1/games/{game['id']}/debug-eval",
        json={"eval_curve": [{"eval": 0.2}, {"eval": 5.3}, {"eval": -1.4}], "analysis_status": "complete"},
    )
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()

    assert response.status_code == 200
    assert response.json()["story"]["primary_story"] == "heartbreaker"
    assert card["story"]["badge_label"] == "Heartbreaker"
    assert card["story"]["headline"] == "Had the game in hand, then watched it slip away."
    assert card["board_position_source"] == "key_position"
    MockAsyncClient.payloads = None


def test_debug_eval_updates_card_into_turning_point(monkeypatch) -> None:
    MockAsyncClient.payloads = [quiet_payload("debug-turning-point", winner=None)]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]

    response = client.post(
        f"/api/v1/games/{game['id']}/debug-eval",
        json={"eval_curve": [{"eval": 0.1}, {"eval": 2.9}, {"eval": 2.7}], "analysis_status": "complete"},
    )
    card = client.get(f"/api/v1/games/{game['id']}/share-card").json()

    assert response.status_code == 200
    assert response.json()["story"]["primary_story"] == "turning_point"
    assert card["story"]["badge_label"] == "Turning Point"
    assert card["metrics"]["biggest_eval_swing"] >= 2.5
    assert card["board_position_source"] == "key_position"
    MockAsyncClient.payloads = None


def test_reprocess_all_updates_stale_headline(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game_id = client.get("/api/v1/games").json()[0]["id"]
    with get_session() as session:
        story = session.scalar(select(GameStory))
        story.primary_story = "daily_activity"
        story.badge_label = "Daily Game"
        story.headline = "Another game added to the chess journal."
        story.interesting_score = 0.1

    response = client.post("/api/v1/games/reprocess-all")
    detail = client.get(f"/api/v1/games/{game_id}")

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    assert detail.json()["story"]["headline"] != "Another game added to the chess journal."


def test_five_real_shape_imported_games_render_share_cards(monkeypatch) -> None:
    MockAsyncClient.payloads = [base_payload(f"real-shape-{index}") for index in range(5)]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()

    response = client.post("/api/v1/games/import/lichess")

    assert response.json()["imported"] == 5
    for game in client.get("/api/v1/games").json():
        card = client.get(f"/api/v1/games/{game['id']}/share-card")
        assert card.status_code == 200
        assert card.json()["story"]["headline"]
        assert card.json()["story"]["key_position_fen"]
    MockAsyncClient.payloads = None


def test_publish_story_creates_public_post(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]

    response = client.post(f"/api/v1/stories/{game['story']['id']}/publish")

    assert response.status_code == 200
    assert response.json()["visibility"] == "public"
    assert response.json()["card_theme"] == "classic"
    assert response.json()["card_size"] == "square"
    assert response.json()["game_story_id"] == game["story"]["id"]
    with get_session() as session:
        assert len(session.scalars(select(PublishedPost)).all()) == 1


def test_publish_story_saves_selected_card_theme(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]

    post = client.post(f"/api/v1/stories/{story_id}/publish", json={"card_theme": "neon_blitz"}).json()
    public_post = client.get(f"/api/v1/posts/{post['id']}").json()
    profile_post = client.get("/api/v1/profiles/clevermike").json()["posts"][0]

    assert post["card_theme"] == "neon_blitz"
    assert public_post["card_theme"] == "neon_blitz"
    assert profile_post["card_theme"] == "neon_blitz"


def test_publish_story_saves_selected_card_size(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]

    post = client.post(
        f"/api/v1/stories/{story_id}/publish",
        json={"card_theme": "newspaper", "card_size": "landscape"},
    ).json()
    public_post = client.get(f"/api/v1/posts/{post['id']}").json()
    profile_post = client.get("/api/v1/profiles/clevermike").json()["posts"][0]

    assert post["card_theme"] == "newspaper"
    assert post["card_size"] == "landscape"
    assert public_post["card_theme"] == "newspaper"
    assert public_post["card_size"] == "landscape"
    assert profile_post["card_size"] == "landscape"


def test_publish_story_unknown_or_locked_theme_falls_back_to_classic(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]

    locked = client.post(f"/api/v1/stories/{story_id}/publish", json={"card_theme": "luxury"}).json()
    unknown = client.post(
        f"/api/v1/stories/{story_id}/publish",
        json={"card_theme": "made_up", "card_size": "poster"},
    ).json()

    assert locked["card_theme"] == "classic"
    assert unknown["card_theme"] == "classic"
    assert unknown["card_size"] == "square"


def test_publish_story_twice_does_not_duplicate(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]

    first = client.post(f"/api/v1/stories/{story_id}/publish").json()
    second = client.post(f"/api/v1/stories/{story_id}/publish").json()

    assert first["id"] == second["id"]
    with get_session() as session:
        assert len(session.scalars(select(PublishedPost)).all()) == 1


def test_unpublish_removes_post_from_public_profile(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]
    post = client.post(f"/api/v1/stories/{story_id}/publish").json()

    response = client.post(f"/api/v1/posts/{post['id']}/unpublish")
    profile = client.get("/api/v1/profiles/clevermike")

    assert response.status_code == 200
    assert response.json()["visibility"] == "unpublished"
    assert profile.status_code == 200
    assert profile.json()["posts"] == []
    assert profile.json()["published_cards_count"] == 0


def test_private_journal_games_do_not_appear_on_public_profile(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")

    profile = client.get("/api/v1/profiles/clevermike")

    assert profile.status_code == 200
    assert profile.json()["posts"] == []
    assert profile.json()["games_imported"] == 1


def test_profile_endpoint_returns_only_public_posts(monkeypatch) -> None:
    MockAsyncClient.payloads = [base_payload("public-one"), base_payload("public-two")]
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    games = client.get("/api/v1/games").json()
    public_post = client.post(f"/api/v1/stories/{games[0]['story']['id']}/publish").json()
    unpublished_post = client.post(f"/api/v1/stories/{games[1]['story']['id']}/publish").json()
    client.post(f"/api/v1/posts/{unpublished_post['id']}/unpublish")

    profile = client.get("/api/v1/profiles/clevermike")

    assert profile.status_code == 200
    assert [post["id"] for post in profile.json()["posts"]] == [public_post["id"]]
    MockAsyncClient.payloads = None


def test_public_profile_display_name_uses_lichess_username_for_local_session(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    session_id = "session-1781471651808-46122pw6o"
    client = connected_client(session_id=session_id)
    client.post("/api/v1/games/import/lichess", headers={"X-Session-Id": session_id})
    story_id = client.get("/api/v1/games", headers={"X-Session-Id": session_id}).json()[0]["story"]["id"]
    client.post(f"/api/v1/stories/{story_id}/publish", headers={"X-Session-Id": session_id})

    response = client.get("/api/v1/profiles/clevermike")
    body = response.json()

    assert response.status_code == 200
    assert body["display_name"] == "clevermike"
    assert body["profile_slug"] == "clevermike"
    assert body["lichess_username"] == "clevermike"
    assert body["published_cards_count"] == 1
    assert "local-session" not in json.dumps(body)


def test_profile_slug_does_not_resolve_internal_local_session_username(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    session_id = "session-1781471651808-46122pw6o"
    client = connected_client(session_id=session_id)

    response = client.get("/api/v1/profiles/local-session-1781471651808-46122pw6o")

    assert response.status_code == 404


def test_profile_resolution_prefers_matching_lichess_account_with_public_posts(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    first_session = "session-no-posts"
    second_session = "session-with-posts"
    client = connected_client(session_id=first_session)
    connected_client(session_id=second_session)
    client.post("/api/v1/games/import/lichess", headers={"X-Session-Id": second_session})
    story_id = client.get("/api/v1/games", headers={"X-Session-Id": second_session}).json()[0]["story"]["id"]
    public_post = client.post(f"/api/v1/stories/{story_id}/publish", headers={"X-Session-Id": second_session}).json()

    profile = client.get("/api/v1/profiles/clevermike")

    assert profile.status_code == 200
    assert profile.json()["published_cards_count"] == 1
    assert [post["id"] for post in profile.json()["posts"]] == [public_post["id"]]


def test_reprocessing_published_story_keeps_public_post_available(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    game = client.get("/api/v1/games").json()[0]
    post = client.post(f"/api/v1/stories/{game['story']['id']}/publish").json()

    reprocess = client.post(f"/api/v1/games/{game['id']}/process")
    public_post = client.get(f"/api/v1/posts/{post['id']}")

    assert reprocess.status_code == 200
    assert public_post.status_code == 200
    assert public_post.json()["headline"] == public_post.json()["story"]["headline"]


def test_public_post_fetches_share_card_data(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    client = connected_client()
    client.post("/api/v1/games/import/lichess")
    story_id = client.get("/api/v1/games").json()[0]["story"]["id"]
    post = client.post(f"/api/v1/stories/{story_id}/publish").json()

    response = client.get(f"/api/v1/posts/{post['id']}")

    assert response.status_code == 200
    assert response.json()["share_card"]["story"]["headline"]
    assert response.json()["share_card"]["game"]["platform"] == "lichess"
    assert response.json()["display_name"] == "clevermike"
    assert "user_id" not in response.json()
    assert "raw_payload" not in response.json()
    assert "pgn" not in json.dumps(response.json()).lower()


def connected_client(session_id: str | None = None) -> TestClient:
    client = TestClient(app)
    headers = {"X-Session-Id": session_id} if session_id else None
    client.get("/api/v1/integrations/lichess/connect", headers=headers, follow_redirects=False)
    with get_session() as session:
        state = session.scalar(select(OAuthState.state))
    client.get(f"/api/v1/integrations/lichess/callback?code=oauth-code&state={state}", follow_redirects=False)
    return client


def base_payload(
    game_id: str,
    *,
    opening: dict[str, str] | None = {"eco": "B20", "name": "Sicilian Defense"},
    players: dict[str, Any] | None = None,
    pgn: str | None = None,
) -> dict[str, Any]:
    return {
        "id": game_id,
        "pgn": (pgn or SAMPLE_PGN).replace("https://lichess.org/example", f"https://lichess.org/{game_id}"),
        "speed": "blitz",
        "clock": {"initial": 300, "increment": 0},
        "createdAt": 1781432100000,
        "opening": opening,
        "players": players
        or {
            "white": {"rating": 1392, "ratingDiff": 14},
            "black": {"rating": 1560, "ratingDiff": -14},
        },
    }


def moves_payload(game_id: str, *, moves: str, winner: str | None = "white") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": game_id,
        "moves": moves,
        "speed": "blitz",
        "clock": {"initial": 300, "increment": 0},
        "createdAt": 1781432100000,
        "opening": {"eco": "A04", "name": "Zukertort Opening"},
        "players": {
            "white": {"user": {"name": "clevermike"}, "rating": 1392, "ratingDiff": 4},
            "black": {"user": {"name": "Bai_Daniil"}, "rating": 1401, "ratingDiff": -4},
        },
    }
    if winner is not None:
        payload["winner"] = winner
    return payload


def quiet_payload(game_id: str, *, winner: str | None) -> dict[str, Any]:
    return moves_payload(
        game_id,
        moves="e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6",
        winner=winner,
    )


def repetition_moves(cycles: int) -> str:
    return " ".join(["Nf3", "Nf6", "Ng1", "Ng8"] * cycles)
