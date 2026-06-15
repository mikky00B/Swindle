from fastapi.testclient import TestClient

from app.main import app


SAMPLE_PGN = """[Event "Rated blitz game"]
[Site "https://lichess.org/example"]
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


def test_pgn_story_endpoint_returns_share_card_contract() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/prototype/pgn-story",
        json={"pgn": SAMPLE_PGN, "username": "clevermike"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["template"] == "generic_square_v1"
    assert body["player"]["username"] == "clevermike"
    assert body["game"]["result"] == "win"
    assert body["game"]["user_color"] == "white"
    assert body["game"]["opening"] == "Sicilian Defense"
    assert body["game"]["moves"] == 31
    assert body["story"]["primary_story"] == "giant_slayer"
    assert body["story"]["headline"] == "Took down a much higher-rated opponent."
    assert body["story"]["key_position_fen"]
    assert body["story"]["key_move_number"] is None
    assert body["board_position_source"] == "final_position"
    assert body["game"]["final_fen"] == body["story"]["key_position_fen"]


def test_pgn_story_endpoint_uses_request_metrics_for_story_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/prototype/pgn-story",
        json={
            "pgn": SAMPLE_PGN,
            "username": "clevermike",
            "metrics": {
                "lowest_eval": -5.2,
                "biggest_eval_swing": 7.4,
                "turning_point_move": 22,
                "eval_curve": [0, -5.2, 1.4],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["story"]["primary_story"] == "swindle"
    assert body["story"]["badge_emoji"] == "SW"
    assert body["story"]["headline"] == "Completely lost, somehow walked out with the full point."
    assert body["story"]["key_move_number"] == 22
    assert body["story"]["key_position_fen"]


def test_pgn_story_endpoint_handles_missing_opening_and_accuracy() -> None:
    client = TestClient(app)
    pgn_without_opening = SAMPLE_PGN.replace('[Opening "Sicilian Defense"]\n', "")

    response = client.post(
        "/api/v1/prototype/pgn-story",
        json={"pgn": pgn_without_opening, "username": "clevermike", "metrics": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["game"]["opening"] is None
    assert body["metrics"]["accuracy"] is None
    assert body["metrics"]["lowest_eval"] is None
    assert body["metrics"]["biggest_eval_swing"] is None


def test_pgn_story_endpoint_includes_black_user_color() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/prototype/pgn-story",
        json={"pgn": SAMPLE_PGN, "username": "higherRated"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["game"]["user_color"] == "black"
    assert body["game"]["result"] == "loss"
