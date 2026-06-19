from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.integrations.lichess.service import ensure_local_user
from app.models import Game, GameSession, GameSessionGame, GameStory, User

STORY_PRIORITY = {
    "rating_milestone": 110,
    "swindle": 100,
    "heartbreaker": 95,
    "giant_slayer": 90,
    "turning_point": 85,
    "clean_game": 80,
    "miniature": 70,
    "long_grind": 60,
    "opening_win": 50,
    "daily_activity": 20,
}

COUNTED_STORIES = {
    "swindle": "swindle_count",
    "heartbreaker": "heartbreaker_count",
    "miniature": "miniature_count",
    "long_grind": "long_grind_count",
    "giant_slayer": "giant_slayer_count",
    "turning_point": "turning_point_count",
}


def rebuild_user_sessions(user_id: str) -> dict[str, int]:
    with get_session() as session:
        ensure_local_user(session, user_id)
        games = (
            session.scalars(
                select(Game)
                .options(joinedload(Game.story))
                .where(Game.user_id == user_id, Game.played_at.is_not(None))
                .order_by(Game.played_at.asc())
            )
            .unique()
            .all()
        )
        session.execute(
            delete(GameSessionGame).where(
                GameSessionGame.session_id.in_(select(GameSession.id).where(GameSession.user_id == user_id))
            )
        )
        session.execute(delete(GameSession).where(GameSession.user_id == user_id))
        created = 0
        for group in _group_games(games):
            recap = _build_session_model(user_id, group)
            session.add(recap)
            session.flush()
            for game in group:
                session.add(GameSessionGame(session_id=recap.id, game_id=game.id))
            created += 1
        return {"sessions": created}


def list_sessions(user_id: str) -> list[dict[str, Any]]:
    with get_session() as session:
        sessions = session.scalars(
            select(GameSession)
            .options(joinedload(GameSession.games).joinedload(GameSessionGame.game))
            .where(GameSession.user_id == user_id)
            .order_by(GameSession.started_at.desc())
        ).unique().all()
        return [
            _session_summary(
                item,
                openings=_opening_breakdown([link.game for link in item.games if link.game is not None]),
                rating_tracks=_rating_tracks([link.game for link in item.games if link.game is not None]),
            )
            for item in sessions
        ]


def get_session_detail(session_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        recap = session.scalar(select(GameSession).where(GameSession.id == session_id, GameSession.user_id == user_id))
        if recap is None:
            return None
        links = (
            session.scalars(
                select(GameSessionGame)
                .options(joinedload(GameSessionGame.game).joinedload(Game.story))
                .where(GameSessionGame.session_id == recap.id)
                .join(Game, GameSessionGame.game_id == Game.id)
                .order_by(Game.played_at.asc())
            )
            .unique()
            .all()
        )
        games = [link.game for link in links if link.game is not None]
        payload = _session_summary(recap, openings=_opening_breakdown(games), rating_tracks=_rating_tracks(games))
        payload["games"] = [_game_summary(link.game) for link in links]
        payload["openings"] = _opening_breakdown(games)
        payload["best_game"] = _game_summary(recap.best_game) if recap.best_game else None
        payload["share_card"] = _session_share_card(recap, links)
        return payload


def get_session_share_card(session_id: str, user_id: str) -> dict[str, Any] | None:
    detail = get_session_detail(session_id, user_id)
    if detail is None:
        return None
    return detail["share_card"]


def _group_games(games: list[Game]) -> list[list[Game]]:
    groups_by_day: dict[datetime.date, list[Game]] = {}
    for game in games:
        if game.played_at is None:
            continue
        groups_by_day.setdefault(game.played_at.date(), []).append(game)
    return [groups_by_day[day] for day in sorted(groups_by_day)]


def _build_session_model(user_id: str, games: list[Game]) -> GameSession:
    wins = sum(1 for game in games if game.result == "win")
    losses = sum(1 for game in games if game.result == "loss")
    draws = sum(1 for game in games if game.result == "draw")
    story_counts = Counter(game.story.primary_story for game in games if game.story is not None)
    best_story = _best_story(games)
    opening = _most_common_opening(games)
    rating_delta = _rating_delta(games)
    mood = _mood(len(games), wins, losses, story_counts)
    headline = _headline(len(games), wins, losses, draws, mood, best_story, rating_delta)
    subheadline = _subheadline(best_story, wins, losses, draws)
    now = datetime.now(timezone.utc)
    return GameSession(
        user_id=user_id,
        started_at=games[0].played_at,
        ended_at=games[-1].played_at,
        games_count=len(games),
        wins_count=wins,
        losses_count=losses,
        draws_count=draws,
        win_rate=wins / len(games) if games else 0,
        best_story_type=best_story.primary_story if best_story else None,
        best_game_id=best_story.game_id if best_story else None,
        best_game_story_id=best_story.id if best_story else None,
        most_common_opening=opening,
        rating_delta=rating_delta,
        mood=mood,
        summary_headline=headline,
        summary_subheadline=subheadline,
        swindle_count=story_counts["swindle"],
        heartbreaker_count=story_counts["heartbreaker"],
        miniature_count=story_counts["miniature"],
        long_grind_count=story_counts["long_grind"],
        giant_slayer_count=story_counts["giant_slayer"],
        turning_point_count=story_counts["turning_point"],
        created_at=now,
        updated_at=now,
    )


def _best_story(games: list[Game]) -> GameStory | None:
    stories = [game.story for game in games if game.story is not None]
    if not stories:
        return None
    return max(stories, key=lambda story: (STORY_PRIORITY.get(story.primary_story, 0), story.interesting_score))


def _most_common_opening(games: list[Game]) -> str:
    openings = [game.opening_name for game in games if game.opening_name]
    if not openings:
        return "Mixed openings"
    opening, count = Counter(openings).most_common(1)[0]
    return opening if count > 1 or len(openings) >= len(games) / 2 else "Mixed openings"


def _rating_delta(games: list[Game]) -> int | None:
    tracks = _rating_tracks(games)
    explicit = sum(track["explicit_delta"] for track in tracks)
    has_explicit = any(track["has_explicit"] for track in tracks)
    inferred = sum(track["inferred_delta"] or 0 for track in tracks)
    has_inferred = any(track["inferred_delta"] is not None for track in tracks)

    if not has_explicit and not has_inferred:
        return None
    return explicit + inferred


def _rating_tracks(games: list[Game]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str | None], list[Game]] = {}
    for game in games:
        grouped.setdefault((game.platform, game.speed), []).append(game)

    tracks: list[dict[str, Any]] = []
    for (platform, speed), group in grouped.items():
        ordered = sorted(group, key=lambda game: game.played_at or datetime.min.replace(tzinfo=timezone.utc))
        explicit_delta = sum(game.rating_change for game in ordered if game.rating_change is not None)
        rating_games = [game for game in ordered if game.rating_change is None and game.user_rating_before is not None]
        inferred_delta = None
        if len(rating_games) >= 2:
            inferred_delta = rating_games[-1].user_rating_before - rating_games[0].user_rating_before
        tracks.append(
            {
                "platform": platform,
                "speed": speed,
                "explicit_delta": explicit_delta,
                "has_explicit": any(game.rating_change is not None for game in ordered),
                "first_rating": rating_games[0].user_rating_before if rating_games else None,
                "last_rating": rating_games[-1].user_rating_before if rating_games else None,
                "first_played_at": _iso(rating_games[0].played_at) if rating_games else None,
                "last_played_at": _iso(rating_games[-1].played_at) if rating_games else None,
                "inferred_delta": inferred_delta,
            }
        )
    return tracks


def _mood(games_count: int, wins: int, losses: int, stories: Counter[str]) -> str:
    if losses >= 4 and losses > wins:
        return "Tilt day"
    if wins >= 4 and wins > losses:
        return "Clean climb"
    if stories["swindle"] >= 1:
        return "Chaos survived"
    if stories["heartbreaker"] >= 1 and losses >= wins:
        return "Painful grind"
    if stories["long_grind"] >= 2:
        return "Endgame marathon"
    if games_count >= 8:
        return "Blitz storm"
    if stories["miniature"] >= 2:
        return "Sharp run"
    return "Balanced battle"


def _headline(games_count: int, wins: int, losses: int, draws: int, mood: str, best_story: GameStory | None, rating_delta: int | None) -> str:
    story_label = _story_label(best_story.primary_story) if best_story else None
    if mood == "Clean climb" and story_label:
        return f"A {games_count}-game day with {wins} wins and a {story_label} highlight."
    if mood == "Tilt day":
        return f"A tough chess day: {wins} wins, {losses} losses, and lessons for the next run."
    if mood == "Chaos survived":
        return f"A chaotic chess day of {games_count} games that somehow found an escape."
    if draws:
        return f"A balanced {games_count}-game day: {wins}W - {losses}L - {draws}D."
    if rating_delta and rating_delta > 0:
        return f"A {games_count}-game chess day that finished positive by {rating_delta} rating points."
    return f"A {games_count}-game chess day added to the journal."


def _opening_breakdown(games: list[Game]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for game in games:
        name = game.opening_name or "Unclassified opening"
        item = grouped.setdefault(name, {"name": name, "games": 0, "wins": 0, "losses": 0, "draws": 0})
        item["games"] += 1
        if game.result == "win":
            item["wins"] += 1
        elif game.result == "loss":
            item["losses"] += 1
        elif game.result == "draw":
            item["draws"] += 1

    breakdown = []
    for item in grouped.values():
        games_count = item["games"]
        breakdown.append(
            {
                **item,
                "record": f"{item['wins']}W - {item['losses']}L - {item['draws']}D",
                "win_rate": item["wins"] / games_count if games_count else 0,
            }
        )
    return sorted(breakdown, key=lambda item: (-item["games"], -item["wins"], item["name"]))


def _subheadline(best_story: GameStory | None, wins: int, losses: int, draws: int) -> str:
    parts = [f"Record: {wins}W - {losses}L - {draws}D."]
    if best_story:
        parts.append(f"Best story: {_story_label(best_story.primary_story)}.")
    return " ".join(parts)


def _story_label(value: str | None) -> str:
    return (value or "Daily Activity").replace("_", " ").title()


def _session_summary(
    recap: GameSession,
    openings: list[dict[str, Any]] | None = None,
    rating_tracks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "id": recap.id,
        "started_at": _iso(recap.started_at),
        "ended_at": _iso(recap.ended_at),
        "games_count": recap.games_count,
        "wins_count": recap.wins_count,
        "losses_count": recap.losses_count,
        "draws_count": recap.draws_count,
        "win_rate": recap.win_rate,
        "best_story_type": recap.best_story_type,
        "best_game_id": recap.best_game_id,
        "best_game_story_id": recap.best_game_story_id,
        "most_common_opening": recap.most_common_opening,
        "rating_delta": recap.rating_delta,
        "mood": recap.mood,
        "summary_headline": recap.summary_headline,
        "summary_subheadline": recap.summary_subheadline,
        "swindle_count": recap.swindle_count,
        "heartbreaker_count": recap.heartbreaker_count,
        "miniature_count": recap.miniature_count,
        "long_grind_count": recap.long_grind_count,
        "giant_slayer_count": recap.giant_slayer_count,
        "turning_point_count": recap.turning_point_count,
    }
    if openings is not None:
        payload["openings"] = openings
    if rating_tracks is not None:
        payload["rating_tracks"] = rating_tracks
    return payload


def _game_summary(game: Game | None) -> dict[str, Any] | None:
    if game is None:
        return None
    return {
        "id": game.id,
        "platform": game.platform,
        "result": game.result,
        "opening_name": game.opening_name,
        "opponent_username": game.opponent_username,
        "moves_count": game.moves_count,
        "played_at": _iso(game.played_at),
        "story": {
            "id": game.story.id,
            "primary_story": game.story.primary_story,
            "badge_label": game.story.badge_label,
            "badge_emoji": game.story.badge_emoji,
            "headline": game.story.headline,
        }
        if game.story
        else None,
    }


def _session_share_card(recap: GameSession, links: list[GameSessionGame]) -> dict[str, Any]:
    username = _session_username(links)
    games = [link.game for link in links if link.game is not None]
    return {
        "kind": "session_recap",
        "template": "session_recap_square_v1",
        "player": {"username": username},
        "session": _session_summary(recap),
        "stats": {
            "record": f"{recap.wins_count}W - {recap.losses_count}L - {recap.draws_count}D",
            "games_count": recap.games_count,
            "best_story": _story_label(recap.best_story_type),
            "most_common_opening": recap.most_common_opening,
            "openings": _opening_breakdown(games),
            "rating_delta": recap.rating_delta,
        },
    }


def _session_username(links: list[GameSessionGame]) -> str:
    for link in links:
        game = link.game
        if game.user_color == "white" and game.white_username:
            return game.white_username
        if game.user_color == "black" and game.black_username:
            return game.black_username
    return "Player"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
