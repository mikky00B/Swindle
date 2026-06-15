from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.games.pgn_parser import compute_final_fen_from_moves, count_moves_from_san, parse_pgn
from app.games.schemas import ParsedGame
from app.games.repository import save_imported_game
from app.integrations.lichess.service import LOCAL_USER_ID, get_connected_account, get_decrypted_access_token
from app.integrations.lichess.service import lichess_api_url
from app.share_cards.schemas import build_share_card_data
from app.story.processor import generate_story


async def import_latest_lichess_games(limit: int = 20, user_id: str = LOCAL_USER_ID) -> dict[str, int]:
    account = get_connected_account(user_id)
    if account is None:
        raise ValueError("No connected Lichess account")

    games = await fetch_latest_games(account, max(10, min(limit, 20)))
    imported = 0
    duplicates = 0
    skipped = 0
    errors: list[str] = []
    for payload in games:
        external_id = str(payload.get("id") or payload.get("gameId") or "")
        if not external_id:
            skipped += 1
            errors.append("Skipped game unknown: missing game id.")
            continue

        try:
            parsed = _parse_payload_game(payload, account["platform_username"])
        except ValueError:
            skipped += 1
            errors.append(f"Skipped game {external_id}: missing or invalid move source.")
            continue
        story = generate_story(parsed)
        share_card = build_share_card_data(parsed, story, None, account["platform_username"])
        did_import, _ = save_imported_game(
            user_id=user_id,
            chess_account_id=account["id"],
            platform="lichess",
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

    return {"imported": imported, "duplicates": duplicates, "skipped": skipped, "total_seen": len(games), "errors": errors}


async def fetch_latest_games(account: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    settings = get_settings()
    username = account["platform_username"]
    token = get_decrypted_access_token(account)
    params = {
        "max": str(limit),
        "pgnInJson": "true",
        "opening": "true",
        "clocks": "true",
        "evals": "false",
        "sort": "dateDesc",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                lichess_api_url(f"/games/user/{username}"),
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/x-ndjson",
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {401, 403}:
                raise ValueError("Lichess account is private, inaccessible, or the token was revoked.") from exc
            if status == 429:
                raise ValueError("Lichess rate limit reached. Wait a moment before importing again.") from exc
            raise ValueError(f"Lichess import failed with status {status}.") from exc
        except httpx.HTTPError as exc:
            raise ValueError("Could not reach Lichess. Check your connection and try again.") from exc
        return [_loads_ndjson(line) for line in response.text.splitlines() if line.strip()]


def _parse_payload_game(payload: dict[str, Any], username: str) -> ParsedGame:
    pgn = payload.get("pgn")
    moves = payload.get("moves")
    parsed: ParsedGame | None = None
    if isinstance(pgn, str) and pgn.strip():
        try:
            parsed = parse_pgn(pgn, username)
        except ValueError:
            parsed = None

    moves_fen = compute_final_fen_from_moves(moves if isinstance(moves, str) else None)
    if parsed is None:
        if not moves_fen or not isinstance(moves, str):
            raise ValueError("missing replayable moves")
        parsed = _parsed_from_moves_payload(payload, username, moves, moves_fen)
    elif moves_fen:
        parsed = parsed.model_copy(update={"final_fen": moves_fen})

    white = parsed.white_username or _player_name(payload, "white")
    black = parsed.black_username or _player_name(payload, "black")
    user_color = parsed.user_color or _detect_user_color(username, white, black)
    winner_color = parsed.winner_color or (payload.get("winner") if payload.get("winner") in {"white", "black"} else None)
    return parsed.model_copy(
        update={
            "white_username": white,
            "black_username": black,
            "user_color": user_color,
            "opponent_username": parsed.opponent_username or _opponent_for_color(user_color, white, black),
            "winner_color": winner_color,
            "result": _result_for_user(winner_color, user_color) if user_color and winner_color else parsed.result,
            "speed": payload.get("speed") or parsed.speed,
            "time_control": _time_control(payload) or parsed.time_control,
            "played_at": _played_at(payload) or parsed.played_at,
            "rating_change": _rating_change(payload, user_color),
            "opening_name": _opening_name(payload) or parsed.opening_name,
            "opening_eco": _opening_eco(payload) or parsed.opening_eco,
            "user_rating_before": _rating(payload, user_color) or parsed.user_rating_before,
            "opponent_rating": _rating(payload, _opposite_color(user_color)) or parsed.opponent_rating,
        }
    )


def _parsed_from_moves_payload(payload: dict[str, Any], username: str, moves: str, final_fen: str) -> ParsedGame:
    white = _player_name(payload, "white")
    black = _player_name(payload, "black")
    user_color = _detect_user_color(username, white, black)
    winner_color = payload.get("winner") if payload.get("winner") in {"white", "black"} else None
    result = _result_for_user(winner_color, user_color)
    return ParsedGame(
        pgn=moves,
        white_username=white,
        black_username=black,
        user_color=user_color,
        opponent_username=_opponent_for_color(user_color, white, black),
        result=result,
        winner_color=winner_color,
        termination=payload.get("status") if isinstance(payload.get("status"), str) else None,
        rated=payload.get("rated") if isinstance(payload.get("rated"), bool) else None,
        speed=payload.get("speed") if isinstance(payload.get("speed"), str) else None,
        time_control=_time_control(payload),
        opening_name=_opening_name(payload),
        opening_eco=_opening_eco(payload),
        moves_count=count_moves_from_san(moves),
        user_rating_before=_rating(payload, user_color),
        opponent_rating=_rating(payload, _opposite_color(user_color)),
        rating_change=_rating_change(payload, user_color),
        played_at=_played_at(payload),
        final_fen=final_fen,
    )


def _loads_ndjson(line: str) -> dict[str, Any]:
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("Expected Lichess game payload object")
    return value


def _time_control(payload: dict[str, Any]) -> str | None:
    clock = payload.get("clock")
    if not isinstance(clock, dict):
        return None
    initial = clock.get("initial")
    increment = clock.get("increment")
    if isinstance(initial, int) and isinstance(increment, int):
        return f"{initial // 60}+{increment}"
    return None


def _played_at(payload: dict[str, Any]) -> datetime | None:
    created_at = payload.get("createdAt")
    if isinstance(created_at, int):
        return datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
    return None


def _rating_change(payload: dict[str, Any], user_color: str | None) -> int | None:
    if user_color not in {"white", "black"}:
        return None
    players = payload.get("players")
    if not isinstance(players, dict):
        return None
    user = players.get(user_color)
    if not isinstance(user, dict):
        return None
    rating_diff = user.get("ratingDiff")
    return rating_diff if isinstance(rating_diff, int) else None


def _rating(payload: dict[str, Any], color: str | None) -> int | None:
    player = _player(payload, color)
    if player is None:
        return None
    rating = player.get("rating")
    return rating if isinstance(rating, int) else None


def _opening_name(payload: dict[str, Any]) -> str | None:
    opening = payload.get("opening")
    if isinstance(opening, dict) and isinstance(opening.get("name"), str):
        return opening["name"]
    return None


def _opening_eco(payload: dict[str, Any]) -> str | None:
    opening = payload.get("opening")
    if isinstance(opening, dict) and isinstance(opening.get("eco"), str):
        return opening["eco"]
    return None


def _player_name(payload: dict[str, Any], color: str) -> str | None:
    player = _player(payload, color)
    if player is None:
        return None
    user = player.get("user")
    if isinstance(user, dict):
        name = user.get("name") or user.get("id")
        if isinstance(name, str):
            return name
    name = player.get("name")
    return name if isinstance(name, str) else None


def _player(payload: dict[str, Any], color: str | None) -> dict[str, Any] | None:
    if color not in {"white", "black"}:
        return None
    players = payload.get("players")
    if not isinstance(players, dict):
        return None
    player = players.get(color)
    return player if isinstance(player, dict) else None


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


def _result_for_user(winner_color: str | None, user_color: str | None) -> str:
    if winner_color is None:
        return "draw"
    if user_color is None:
        return "win"
    return "win" if winner_color == user_color else "loss"


def _opposite_color(color: str | None) -> str | None:
    if color == "white":
        return "black"
    if color == "black":
        return "white"
    return None
