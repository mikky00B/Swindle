from __future__ import annotations

from dataclasses import dataclass

from app.games.schemas import GameMetrics, ParsedGame


STORY_PRIORITY = {
    "rating_milestone": 110,
    "swindle": 100,
    "heartbreaker": 95,
    "giant_slayer": 90,
    "clean_game": 80,
    "miniature": 70,
    "long_grind": 60,
    "opening_win": 50,
    "rough_loss": 40,
    "daily_activity": 20,
}

RATING_MILESTONES = (1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400)


@dataclass(frozen=True)
class StoryCandidate:
    story_type: str
    confidence: float
    reasons: tuple[str, ...]


def detect_story_candidates(game: ParsedGame, metrics: GameMetrics | None) -> list[StoryCandidate]:
    candidates: list[StoryCandidate] = []
    metrics = metrics or GameMetrics()

    if _crossed_rating_milestone(game):
        candidates.append(StoryCandidate("rating_milestone", 0.98, ("rating_threshold_crossed",)))

    if game.result == "win" and metrics.lowest_eval is not None and metrics.lowest_eval <= -3:
        confidence = 0.95 if metrics.lowest_eval <= -5 and metrics.eval_curve else 0.70
        candidates.append(StoryCandidate("swindle", confidence, ("lowest_eval_below_minus_3", "won_game")))

    if game.result == "loss" and metrics.highest_eval is not None and metrics.highest_eval >= 3:
        confidence = 0.92 if metrics.highest_eval >= 5 and metrics.eval_curve else 0.70
        candidates.append(StoryCandidate("heartbreaker", confidence, ("highest_eval_above_plus_3", "lost_game")))

    if (
        game.result == "win"
        and game.user_rating_before is not None
        and game.opponent_rating is not None
        and game.opponent_rating - game.user_rating_before >= 150
    ):
        candidates.append(StoryCandidate("giant_slayer", 0.98, ("opponent_rating_gap_150_plus", "won_game")))

    if game.result == "win" and metrics.accuracy is not None and metrics.accuracy >= 90 and game.moves_count >= 25:
        candidates.append(StoryCandidate("clean_game", 0.9, ("accuracy_90_plus", "won_game")))

    if game.result == "win" and game.moves_count <= 25:
        candidates.append(StoryCandidate("miniature", 0.9, ("won_under_25_moves",)))

    if game.moves_count >= 70:
        candidates.append(StoryCandidate("long_grind", 0.9, ("moves_70_plus",)))

    if not candidates:
        candidates.append(StoryCandidate("daily_activity", 0.75, ("journal_entry",)))

    return sorted(candidates, key=lambda item: STORY_PRIORITY[item.story_type], reverse=True)


def _crossed_rating_milestone(game: ParsedGame) -> bool:
    if game.user_rating_before is None or game.user_rating_after is None:
        return False
    return any(game.user_rating_before < milestone <= game.user_rating_after for milestone in RATING_MILESTONES)
