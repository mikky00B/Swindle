from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.integrations.chesscom.client import ChessComClient, ChessComNotFound
from app.main import app
from app.models import ChessAccount, Game, GameStory


CHESSCOM_PGN = """[Event "Live Chess"]
[Site "https://www.chess.com/game/live/123"]
[Date "2026.06.14"]
[White "clevermike"]
[Black "higherRated"]
[Result "1-0"]
[UTCDate "2026.06.14"]
[UTCTime "10:15:00"]
[WhiteElo "1392"]
[BlackElo "1560"]
[ECO "B20"]
[Opening "Sicilian Defense"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6 6. Be3 Be7 7. f3 O-O
8. Qd2 Nc6 9. O-O-O a6 10. g4 Qc7 11. h4 b5 12. h5 Nd7 13. g5 Nxd4
14. Qxd4 Bb7 15. h6 e5 16. Qd2 g6 17. Kb1 Rac8 18. Bh3 Rfd8 19. Rh2 b4
20. Nd5 Bxd5 21. Qxd5 Rb8 22. f4 Rb5 23. Qb3 Nc5 24. Bxc5 dxc5 25. Rxd8+
Bxd8 26. Rd2 exf4 27. Qd5 Rb8 28. e5 Bxg5 29. e6 Bxh6 30. exf7+ Qxf7
31. Be6 1-0"""


class MockChessComAsyncClient:
    player_status_code: int = 200
    archives: list[str] = ["https://api.chess.com/pub/player/clevermike/games/2026/06"]
    games: list[dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "MockChessComAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        if url.endswith("/player/clevermike"):
            if self.player_status_code != 200:
                return httpx.Response(self.player_status_code, json={}, request=httpx.Request("GET", url))
            return httpx.Response(
                200,
                json={"username": "clevermike", "player_id": 12345, "url": "https://www.chess.com/member/clevermike"},
                request=httpx.Request("GET", url),
            )
        if url.endswith("/player/clevermike/games/archives"):
            return httpx.Response(200, json={"archives": self.archives}, request=httpx.Request("GET", url))
        if url in self.archives:
            games = self.games or [chesscom_game("https://www.chess.com/game/live/123")]
            return httpx.Response(200, json={"games": games}, request=httpx.Request("GET", url))
        return httpx.Response(404, json={}, request=httpx.Request("GET", url))


def test_chesscom_player_lookup_success(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)

    profile = asyncio.run(ChessComClient().get_player("clevermike"))

    assert profile["username"] == "clevermike"


def test_chesscom_player_not_found(monkeypatch) -> None:
    MockChessComAsyncClient.player_status_code = 404
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)

    try:
        asyncio.run(ChessComClient().get_player("clevermike"))
        raise AssertionError("expected ChessComNotFound")
    except ChessComNotFound:
        pass

    MockChessComAsyncClient.player_status_code = 200


def test_chesscom_archives_fetch_success(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)

    archives = asyncio.run(ChessComClient().get_archives("clevermike"))

    assert archives == ["https://api.chess.com/pub/player/clevermike/games/2026/06"]


def test_chesscom_link_status_disconnect(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    link = client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})
    status = client.get("/api/v1/integrations/chesscom/status")
    disconnect = client.post("/api/v1/integrations/chesscom/disconnect")
    disconnected_status = client.get("/api/v1/integrations/chesscom/status")

    assert link.status_code == 200
    assert link.json()["connected"] is True
    assert link.json()["platform_username"] == "clevermike"
    assert status.json()["connected"] is True
    assert disconnect.json()["disconnected"] is True
    assert disconnected_status.json()["connected"] is False


def test_chesscom_latest_games_import_parses_pgn_and_generates_story(monkeypatch) -> None:
    MockChessComAsyncClient.games = [chesscom_game("https://www.chess.com/game/live/123")]
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})
    response = client.post("/api/v1/games/import/chesscom")

    assert response.status_code == 200
    assert response.json()["imported"] == 1
    journal = client.get("/api/v1/games").json()
    assert len(journal) == 1
    assert journal[0]["platform"] == "chesscom"
    assert journal[0]["final_fen"]
    assert journal[0]["story"]["primary_story"] == "giant_slayer"
    card = client.get(f"/api/v1/games/{journal[0]['id']}/share-card").json()
    assert card["game"]["platform"] == "chesscom"


def test_chesscom_import_derives_opening_from_eco_url_when_opening_header_is_missing(monkeypatch) -> None:
    pgn = CHESSCOM_PGN.replace('[Opening "Sicilian Defense"]\n', '[ECOUrl "https://www.chess.com/openings/Sicilian-Defense-Open-Najdorf-6.Bg5"]\n')
    MockChessComAsyncClient.games = [chesscom_game("https://www.chess.com/game/live/eco-url", pgn=pgn)]
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})
    response = client.post("/api/v1/games/import/chesscom")

    assert response.status_code == 200
    journal = client.get("/api/v1/games").json()
    assert journal[0]["opening_name"] == "Sicilian Defense Open Najdorf"


def test_chesscom_games_without_pgn_are_skipped(monkeypatch) -> None:
    MockChessComAsyncClient.games = [{"url": "https://www.chess.com/game/live/no-pgn"}]
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})
    response = client.post("/api/v1/games/import/chesscom")

    assert response.status_code == 200
    assert response.json()["imported"] == 0
    assert response.json()["skipped"] == 1
    assert "no PGN" in response.json()["errors"][0]


def test_duplicate_chesscom_games_are_not_reimported(monkeypatch) -> None:
    MockChessComAsyncClient.games = [chesscom_game("https://www.chess.com/game/live/dup")]
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})
    first = client.post("/api/v1/games/import/chesscom")
    second = client.post("/api/v1/games/import/chesscom")

    assert first.json()["imported"] == 1
    assert second.json()["duplicates"] == 1
    with get_session_for_test() as session:
        games = session.scalars(select(Game).where(Game.platform == "chesscom")).all()
        stories = session.scalars(select(GameStory)).all()
    assert len(games) == 1
    assert len(stories) == 1


def test_chesscom_account_stores_public_profile_without_tokens(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", MockChessComAsyncClient)
    client = TestClient(app)

    client.post("/api/v1/integrations/chesscom/link", json={"username": "clevermike"})

    with get_session_for_test() as session:
        account = session.scalar(select(ChessAccount).where(ChessAccount.platform == "chesscom"))
        assert account is not None
        assert account.access_token_encrypted is None
        assert account.refresh_token_encrypted is None
        assert account.raw_profile["username"] == "clevermike"


def chesscom_game(url: str, pgn: str | None = None) -> dict[str, Any]:
    return {
        "url": url,
        "pgn": (pgn or CHESSCOM_PGN).replace("https://www.chess.com/game/live/123", url),
        "time_control": "300+0",
        "time_class": "blitz",
        "rated": True,
        "white": {"username": "clevermike", "rating": 1392, "result": "win"},
        "black": {"username": "higherRated", "rating": 1560, "result": "checkmated"},
        "end_time": 1781432100,
    }


def get_session_for_test():
    from app.core.database import get_session

    return get_session()
