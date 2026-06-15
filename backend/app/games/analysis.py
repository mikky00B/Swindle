from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from math import ceil
from typing import Any

import chess
import chess.pgn
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.games.schemas import GameMetrics, ParsedGame
from app.integrations.lichess.service import lichess_api_url
from app.models import EvalCache


MAX_CLOUD_EVAL_POSITIONS = 40
MATE_SCORE = 10.0


@dataclass(frozen=True)
class ReplayPosition:
    fen: str
    move_number: int
    san: str | None


@dataclass(frozen=True)
class EvalPoint:
    fen: str
    move_number: int
    san: str | None
    white_eval: float
    user_eval: float
    depth: int | None


class CloudEvalUnavailable(Exception):
    def __init__(self, message: str, *, cacheable: bool = False) -> None:
        super().__init__(message)
        self.cacheable = cacheable


def analyze_game_with_cloud_eval(game: ParsedGame, session: Session) -> GameMetrics:
    positions = replay_full_move_positions(game, limit=MAX_CLOUD_EVAL_POSITIONS)
    points: list[EvalPoint] = []

    for position in positions:
        cached = get_or_fetch_cloud_eval(session, position.fen)
        if cached is None:
            continue
        white_eval = eval_payload_to_white_pawns(cached)
        if white_eval is None:
            continue
        points.append(
            EvalPoint(
                fen=position.fen,
                move_number=position.move_number,
                san=position.san,
                white_eval=white_eval,
                user_eval=normalize_eval_for_user(white_eval, game.user_color),
                depth=cached.get("depth"),
            )
        )

    return metrics_from_eval_points(points, len(positions))


def metrics_from_mock_user_evals(game: ParsedGame, eval_curve: list[Any], analysis_status: str = "complete") -> GameMetrics:
    replay_positions = replay_full_move_positions(game, limit=max(len(eval_curve), 1))
    points: list[EvalPoint] = []
    for index, item in enumerate(eval_curve):
        value = item.get("eval") if isinstance(item, dict) else getattr(item, "eval", None)
        if value is None:
            continue
        replay = replay_positions[index] if index < len(replay_positions) else None
        fen = _field(item, "fen") or (replay.fen if replay else game.final_fen)
        if not fen:
            continue
        move_number = _field(item, "move") or (replay.move_number if replay else index + 1)
        san = _field(item, "san") or (replay.san if replay else None)
        depth = _field(item, "depth")
        user_eval = round(float(value), 2)
        white_eval = user_eval if game.user_color != "black" else -user_eval
        points.append(
            EvalPoint(
                fen=fen,
                move_number=int(move_number),
                san=san,
                white_eval=white_eval,
                user_eval=user_eval,
                depth=depth,
            )
        )
    metrics = metrics_from_eval_points(points, len(points))
    return metrics.model_copy(update={"analysis_source": "debug_mock_eval", "analysis_status": analysis_status})


def replay_full_move_positions(game: ParsedGame, limit: int = MAX_CLOUD_EVAL_POSITIONS) -> list[ReplayPosition]:
    board = chess.Board()
    moves: list[chess.Move] = []

    pgn_game = chess.pgn.read_game(StringIO(game.pgn or ""))
    if pgn_game is not None:
        moves = list(pgn_game.mainline_moves())
    elif game.pgn:
        for token in game.pgn.split():
            try:
                moves.append(board.parse_san(token))
                board.push(moves[-1])
            except ValueError:
                return []
        board.reset()

    positions: list[ReplayPosition] = []
    for ply, move in enumerate(moves, start=1):
        try:
            san = board.san(move)
        except AssertionError:
            san = None
        board.push(move)
        if ply % 2 != 0:
            continue
        positions.append(ReplayPosition(fen=board.fen(), move_number=ceil(ply / 2), san=san))
        if len(positions) >= limit:
            break
    return positions


def get_or_fetch_cloud_eval(session: Session, fen: str) -> dict[str, Any] | None:
    key = fen_key(fen)
    cached = session.scalar(select(EvalCache).where(EvalCache.fen_key == key))
    if cached is not None:
        payload = _cache_to_eval_payload(cached)
        if payload is not None:
            return payload
        session.delete(cached)
        session.flush()

    try:
        payload = fetch_cloud_eval(fen)
    except CloudEvalUnavailable as exc:
        return None

    if payload is None:
        return None

    cache = EvalCache(
        fen_key=key,
        raw_fen=fen,
        eval_cp=payload.get("cp"),
        mate=payload.get("mate"),
        depth=payload.get("depth"),
        source="lichess_cloud_eval",
    )
    session.add(cache)
    session.flush()
    return payload


def fetch_cloud_eval(fen: str) -> dict[str, Any] | None:
    try:
        chess.Board(fen)
    except ValueError as exc:
        raise CloudEvalUnavailable("invalid fen", cacheable=True) from exc

    try:
        with httpx.Client(timeout=8, trust_env=False) as client:
            response = client.get(lichess_api_url("/cloud-eval"), params={"fen": fen, "multiPv": "1"})
    except httpx.HTTPError as exc:
        raise CloudEvalUnavailable("cloud eval request failed") from exc

    if response.status_code in {204, 404}:
        raise CloudEvalUnavailable("cloud eval unavailable", cacheable=True)
    if response.status_code == 429:
        raise CloudEvalUnavailable("cloud eval rate limited")
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise CloudEvalUnavailable("cloud eval failed") from exc

    body = response.json()
    pvs = body.get("pvs") if isinstance(body, dict) else None
    if not isinstance(pvs, list) or not pvs:
        raise CloudEvalUnavailable("cloud eval missing pvs", cacheable=True)
    first = pvs[0]
    if not isinstance(first, dict):
        raise CloudEvalUnavailable("cloud eval malformed pv", cacheable=True)
    cp = first.get("cp")
    mate = first.get("mate")
    if not isinstance(cp, int) and not isinstance(mate, int):
        raise CloudEvalUnavailable("cloud eval missing score", cacheable=True)
    return {
        "cp": cp if isinstance(cp, int) else None,
        "mate": mate if isinstance(mate, int) else None,
        "depth": body.get("depth") if isinstance(body.get("depth"), int) else None,
    }


def eval_payload_to_white_pawns(payload: dict[str, Any]) -> float | None:
    cp = payload.get("cp")
    if isinstance(cp, int):
        return round(cp / 100, 2)
    mate = payload.get("mate")
    if isinstance(mate, int):
        return float(MATE_SCORE if mate > 0 else -MATE_SCORE)
    return None


def normalize_eval_for_user(white_eval: float, user_color: str | None) -> float:
    return round(white_eval if user_color != "black" else -white_eval, 2)


def metrics_from_eval_points(points: list[EvalPoint], attempted_positions: int) -> GameMetrics:
    if not points:
        return GameMetrics(
            eval_curve=[],
            analysis_source="metadata_only",
            analysis_status="unavailable",
        )

    lowest = min(points, key=lambda point: point.user_eval)
    highest = max(points, key=lambda point: point.user_eval)
    swing = _biggest_swing(points)
    status = "complete" if attempted_positions > 0 and len(points) == attempted_positions else "partial"

    return GameMetrics(
        lowest_eval=lowest.user_eval,
        highest_eval=highest.user_eval,
        biggest_eval_swing=swing["amount"],
        turning_point_move=swing["move_number"],
        turning_point_fen=swing["fen"],
        turning_point_san=swing["san"],
        lowest_eval_fen=lowest.fen,
        highest_eval_fen=highest.fen,
        eval_curve=[
            {
                "move": point.move_number,
                "fen": point.fen,
                "san": point.san,
                "eval": point.user_eval,
                "depth": point.depth,
            }
            for point in points
        ],
        analysis_depth=max((point.depth or 0 for point in points), default=None) or None,
        analysis_source="lichess_cloud_eval",
        analysis_status=status,
    )


def fen_key(fen: str) -> str:
    return sha256(normalize_fen(fen).encode("utf-8")).hexdigest()


def normalize_fen(fen: str) -> str:
    board = chess.Board(fen)
    parts = board.fen().split(" ")
    return " ".join(parts[:4])


def _biggest_swing(points: list[EvalPoint]) -> dict[str, Any]:
    if len(points) < 2:
        point = points[0]
        return {"amount": 0.0, "fen": point.fen, "move_number": point.move_number, "san": point.san}

    best_previous = points[0]
    best_current = points[1]
    best_amount = abs(points[1].user_eval - points[0].user_eval)
    for previous, current in zip(points, points[1:]):
        amount = abs(current.user_eval - previous.user_eval)
        if amount > best_amount:
            best_previous = previous
            best_current = current
            best_amount = amount
    return {
        "amount": round(best_amount, 2),
        "fen": best_previous.fen,
        "move_number": best_current.move_number,
        "san": best_current.san,
    }


def _cache_to_eval_payload(cache: EvalCache) -> dict[str, Any] | None:
    if cache.eval_cp is None and cache.mate is None:
        return None
    return {"cp": cache.eval_cp, "mate": cache.mate, "depth": cache.depth}


def _field(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)
