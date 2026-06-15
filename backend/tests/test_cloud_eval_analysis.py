from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_session
from app.games import analysis
from app.games.analysis import (
    CloudEvalUnavailable,
    EvalPoint,
    get_or_fetch_cloud_eval,
    metrics_from_eval_points,
    normalize_eval_for_user,
)
from app.games.schemas import GameMetrics, ParsedGame
from app.models import EvalCache
from app.story.processor import generate_story


def test_user_eval_normalization_for_white() -> None:
    assert normalize_eval_for_user(2.4, "white") == 2.4


def test_user_eval_normalization_for_black() -> None:
    assert normalize_eval_for_user(2.4, "black") == -2.4


def test_swindle_detection_from_eval_curve() -> None:
    game = ParsedGame(pgn="", result="win", moves_count=42)
    metrics = GameMetrics(lowest_eval=-5.1, eval_curve=[{"move": 20, "eval": -5.1}])

    story = generate_story(game, metrics)

    assert story.primary_story == "swindle"
    assert story.confidence_score == 0.95


def test_heartbreaker_detection_from_eval_curve() -> None:
    game = ParsedGame(pgn="", result="loss", moves_count=42)
    metrics = GameMetrics(highest_eval=5.1, eval_curve=[{"move": 20, "eval": 5.1}])

    story = generate_story(game, metrics)

    assert story.primary_story == "heartbreaker"
    assert story.confidence_score == 0.92


def test_biggest_swing_and_turning_point_fen_selection() -> None:
    points = [
        EvalPoint("fen-a", 10, "Nf3", 0.2, 0.2, 20),
        EvalPoint("fen-b", 11, "Qh5", -0.4, -0.4, 20),
        EvalPoint("fen-c", 12, "Bxh7+", 4.2, 4.2, 20),
    ]

    metrics = metrics_from_eval_points(points, attempted_positions=3)

    assert metrics.biggest_eval_swing == 4.6
    assert metrics.turning_point_fen == "fen-b"
    assert metrics.turning_point_move == 12
    assert metrics.turning_point_san == "Bxh7+"


def test_no_eval_data_falls_back_to_metadata_story() -> None:
    game = ParsedGame(pgn="", result="draw", moves_count=38)
    metrics = metrics_from_eval_points([], attempted_positions=10)

    story = generate_story(game, metrics)

    assert metrics.analysis_status == "unavailable"
    assert story.primary_story == "daily_activity"


def test_cloud_eval_cache_hit_avoids_duplicate_external_call(monkeypatch) -> None:
    calls = 0
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"

    def fake_fetch(target_fen: str) -> dict:
        nonlocal calls
        calls += 1
        return {"cp": 34, "mate": None, "depth": 22}

    monkeypatch.setattr(analysis, "fetch_cloud_eval", fake_fetch)

    with get_session() as session:
        first = get_or_fetch_cloud_eval(session, fen)
        second = get_or_fetch_cloud_eval(session, fen)
        rows = session.scalars(select(EvalCache)).all()

    assert first == second
    assert calls == 1
    assert len(rows) == 1


def test_transient_cloud_eval_failure_does_not_poison_cache(monkeypatch) -> None:
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"

    def fake_fetch(target_fen: str) -> dict:
        raise CloudEvalUnavailable("timeout")

    monkeypatch.setattr(analysis, "fetch_cloud_eval", fake_fetch)

    with get_session() as session:
        result = get_or_fetch_cloud_eval(session, fen)
        rows = session.scalars(select(EvalCache)).all()

    assert result is None
    assert rows == []
