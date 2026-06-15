from app.games.schemas import GameMetrics, ParsedGame
from app.story.detectors import StoryCandidate


BASE_SCORES = {
    "rating_milestone": 0.85,
    "swindle": 0.40,
    "heartbreaker": 0.35,
    "giant_slayer": 0.75,
    "clean_game": 0.25,
    "miniature": 0.75,
    "long_grind": 0.70,
    "daily_activity": 0.15,
}


def calculate_interesting_score(
    game: ParsedGame,
    metrics: GameMetrics | None,
    candidates: list[StoryCandidate],
) -> float:
    metrics = metrics or GameMetrics()
    score = sum(BASE_SCORES.get(candidate.story_type, 0) for candidate in candidates[:2])

    if metrics.biggest_eval_swing is not None and metrics.biggest_eval_swing >= 4:
        score += 0.20
    if (
        game.opponent_rating is not None
        and game.user_rating_before is not None
        and game.opponent_rating - game.user_rating_before >= 150
    ):
        score += 0.20
    if metrics.moves_under_time_pressure is not None and metrics.moves_under_time_pressure >= 5:
        score += 0.15

    return round(min(score, 1.0), 2)
