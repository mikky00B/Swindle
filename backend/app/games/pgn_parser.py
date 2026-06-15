from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from math import ceil

import chess.pgn

from app.games.schemas import ParsedGame


RESULT_MAP = {
    "1-0": ("win", "white"),
    "0-1": ("win", "black"),
    "1/2-1/2": ("draw", None),
    "*": ("unknown", None),
}

RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}


def parse_pgn(pgn: str, username: str | None = None) -> ParsedGame:
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        raise ValueError("Invalid PGN")

    headers = game.headers
    white = _clean_header(headers.get("White"))
    black = _clean_header(headers.get("Black"))
    result_tag = headers.get("Result", "*")
    normalized_result, winner_color = RESULT_MAP.get(result_tag, ("unknown", None))
    plies_count = sum(1 for _ in game.mainline_moves())
    moves_count = ceil(plies_count / 2)
    final_board = game.end().board()

    user_color = _detect_user_color(username, white, black)
    opponent_username = _opponent_for_color(user_color, white, black)
    result = _result_for_user(normalized_result, winner_color, user_color)
    user_rating_before = _rating_for_color(user_color, headers, "Elo")
    opponent_rating = _rating_for_color(_opposite_color(user_color), headers, "Elo")
    played_at = _played_at(headers)

    return ParsedGame(
        pgn=pgn,
        white_username=white,
        black_username=black,
        user_color=user_color,
        opponent_username=opponent_username,
        result=result,
        winner_color=winner_color,
        termination=_clean_header(headers.get("Termination")),
        rated=_rated(headers),
        speed=_clean_header(headers.get("Event")),
        time_control=_clean_header(headers.get("TimeControl")),
        opening_name=_clean_header(headers.get("Opening")),
        opening_eco=_clean_header(headers.get("ECO")),
        moves_count=moves_count,
        user_rating_before=user_rating_before,
        opponent_rating=opponent_rating,
        played_at=played_at,
        final_fen=final_board.fen(),
    )


def compute_final_fen_from_moves(moves: str | None) -> str | None:
    if not moves or not moves.strip():
        return None

    board = chess.Board()
    for token in moves.split():
        token = token.strip()
        if _ignore_move_token(token):
            continue
        try:
            board.push_san(token)
        except ValueError:
            return None
    return board.fen()


def compute_final_fen_from_pgn(pgn: str | None) -> str | None:
    if not pgn or not pgn.strip():
        return None
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        return None
    return game.end().board().fen()


def count_moves_from_san(moves: str | None) -> int:
    if not moves or not moves.strip():
        return 0
    plies = sum(1 for token in moves.split() if not _ignore_move_token(token.strip()))
    return ceil(plies / 2)


def _ignore_move_token(token: str) -> bool:
    if not token:
        return True
    if token in RESULT_TOKENS:
        return True
    if token.startswith("{") or token.startswith(";"):
        return True
    stripped = token.rstrip(".")
    return stripped.isdigit()


def _clean_header(value: str | None) -> str | None:
    if value is None or value == "?":
        return None
    return value


def _detect_user_color(username: str | None, white: str | None, black: str | None) -> str | None:
    if not username:
        return None
    candidate = username.casefold()
    if white and white.casefold() == candidate:
        return "white"
    if black and black.casefold() == candidate:
        return "black"
    return None


def _opposite_color(color: str | None) -> str | None:
    if color == "white":
        return "black"
    if color == "black":
        return "white"
    return None


def _opponent_for_color(color: str | None, white: str | None, black: str | None) -> str | None:
    if color == "white":
        return black
    if color == "black":
        return white
    return None


def _result_for_user(result: str, winner_color: str | None, user_color: str | None) -> str:
    if result in {"draw", "unknown"}:
        return result
    if not user_color:
        return result
    return "win" if winner_color == user_color else "loss"


def _rating_for_color(color: str | None, headers: chess.pgn.Headers, suffix: str) -> int | None:
    if color not in {"white", "black"}:
        return None
    value = headers.get(f"{color.title()}{suffix}")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _rated(headers: chess.pgn.Headers) -> bool | None:
    event = headers.get("Event")
    if event is None:
        return None
    lowered = event.casefold()
    if "rated" in lowered:
        return True
    if "casual" in lowered or "unrated" in lowered:
        return False
    return None


def _played_at(headers: chess.pgn.Headers) -> datetime | None:
    utc_date = headers.get("UTCDate") or headers.get("Date")
    utc_time = headers.get("UTCTime")
    if not utc_date or "?" in utc_date:
        return None
    value = f"{utc_date} {utc_time or '00:00:00'}"
    try:
        return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
