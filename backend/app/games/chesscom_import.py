from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.games.pgn_parser import parse_pgn
from app.games.repository import save_imported_game
from app.games.schemas import ParsedGame
from app.integrations.chesscom.client import ChessComClient, ChessComClientError
from app.integrations.chesscom.service import get_chesscom_account, mark_chesscom_synced
from app.integrations.lichess.service import LOCAL_USER_ID
from app.share_cards.schemas import build_share_card_data
from app.story.processor import generate_story


async def import_latest_chesscom_games(limit: int = 20, user_id: str = LOCAL_USER_ID) -> dict[str, Any]:
    account = get_chesscom_account(user_id)
    if account is None:
        raise ValueError("Add a Chess.com username before importing Chess.com games.")

    username = account["platform_username"]
    try:
        games = await ChessComClient().get_latest_games(username, max(1, min(limit, 20)))
    except ChessComClientError:
        raise

    imported = 0
    duplicates = 0
    skipped = 0
    errors: list[str] = []
    first_seen_id: str | None = None
    for payload in games:
        pgn = payload.get("pgn")
        external_id = _external_game_id(payload)
        if first_seen_id is None:
            first_seen_id = external_id
        if not isinstance(pgn, str) or not pgn.strip():
            skipped += 1
            errors.append(f"Skipped game {external_id}: no PGN in public Chess.com archive.")
            continue
        try:
            parsed = _parse_chesscom_game(payload, username)
        except ValueError:
            skipped += 1
            errors.append(f"Skipped game {external_id}: invalid PGN.")
            continue
        story = generate_story(parsed)
        share_card = build_share_card_data(parsed, story, None, username, "chesscom")
        did_import, _ = save_imported_game(
            user_id=user_id,
            chess_account_id=account["id"],
            platform="chesscom",
            external_game_id=external_id,
            raw_payload=payload,
            parsed_game=parsed,
            story=story,
            share_card=share_card,
        )
        if did_import:
            imported += 1
        else:
            duplicates += 1

    mark_chesscom_synced(user_id, first_seen_id)
    if not games:
        errors.append("No public Chess.com game archives found.")
    elif imported == 0 and skipped == len(games):
        errors.append("No PGN games found in recent Chess.com archives.")
    return {"imported": imported, "duplicates": duplicates, "skipped": skipped, "total_seen": len(games), "errors": errors}


def _parse_chesscom_game(payload: dict[str, Any], username: str) -> ParsedGame:
    pgn = payload.get("pgn")
    if not isinstance(pgn, str) or not pgn.strip():
        raise ValueError("missing pgn")
    parsed = parse_pgn(pgn, username)
    white = _player_username(payload, "white") or parsed.white_username
    black = _player_username(payload, "black") or parsed.black_username
    user_color = parsed.user_color or _detect_user_color(username, white, black)
    return parsed.model_copy(
        update={
            "white_username": white,
            "black_username": black,
            "user_color": user_color,
            "opponent_username": parsed.opponent_username or _opponent_for_color(user_color, white, black),
            "rated": payload.get("rated") if isinstance(payload.get("rated"), bool) else parsed.rated,
            "speed": payload.get("time_class") if isinstance(payload.get("time_class"), str) else parsed.speed,
            "time_control": payload.get("time_control") if isinstance(payload.get("time_control"), str) else parsed.time_control,
            "opening_name": parsed.opening_name or _opening_name_from_pgn(pgn),
            "user_rating_before": _rating(payload, user_color) or parsed.user_rating_before,
            "opponent_rating": _rating(payload, _opposite_color(user_color)) or parsed.opponent_rating,
        }
    )


def _external_game_id(payload: dict[str, Any]) -> str:
    url = payload.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    pgn = payload.get("pgn")
    key = pgn if isinstance(pgn, str) and pgn.strip() else repr(sorted(payload.items()))
    return f"chesscom:{sha256(key.encode('utf-8')).hexdigest()}"


def _player_username(payload: dict[str, Any], color: str) -> str | None:
    player = payload.get(color)
    if not isinstance(player, dict):
        return None
    username = player.get("username")
    return username if isinstance(username, str) else None


def _rating(payload: dict[str, Any], color: str | None) -> int | None:
    if color not in {"white", "black"}:
        return None
    player = payload.get(color)
    if not isinstance(player, dict):
        return None
    rating = player.get("rating")
    return rating if isinstance(rating, int) else None


def _detect_user_color(username: str | None, white: str | None, black: str | None) -> str | None:
    if not username:
        return None
    candidate = username.casefold()
    if white and white.casefold() == candidate:
        return "white"
    if black and black.casefold() == candidate:
        return "black"
    return None


def _opponent_for_color(color: str | None, white: str | None, black: str | None) -> str | None:
    if color == "white":
        return black
    if color == "black":
        return white
    return None


def _opposite_color(color: str | None) -> str | None:
    if color == "white":
        return "black"
    if color == "black":
        return "white"
    return None


def _opening_name_from_pgn(pgn: str) -> str | None:
    eco_url = _pgn_header(pgn, "ECOUrl")
    if not eco_url:
        return None
    marker = "/openings/"
    if marker not in eco_url:
        return None
    slug = eco_url.split(marker, 1)[1].split("?", 1)[0].strip("/")
    if not slug:
        return None
    name = slug.replace("_", "-").replace("-", " ")
    return " ".join(part for part in name.split() if not _looks_like_move_token(part)) or None


def _pgn_header(pgn: str, name: str) -> str | None:
    prefix = f'[{name} "'
    for line in pgn.splitlines():
        if line.startswith(prefix) and line.endswith('"]'):
            return line[len(prefix) : -2]
    return None


def _looks_like_move_token(value: str) -> bool:
    token = value.strip()
    if not token:
        return True
    if token[0].isdigit():
        return True
    return token in {"e4", "e5", "d4", "d5", "c4", "c5", "Nf3", "Nc3", "Bb5", "Bc4"}
