from app.games.schemas import GameMetrics, ParsedGame
from app.story.detectors import detect_story_candidates
from app.story.schemas import GameStory
from app.story.scoring import calculate_interesting_score
from app.story.templates import BADGES, HEADLINE_TEMPLATES, SOFT_HEADLINE_TEMPLATES


def generate_story(game: ParsedGame, metrics: GameMetrics | None = None) -> GameStory:
    candidates = detect_story_candidates(game, metrics)
    primary = candidates[0]
    secondary = candidates[1] if len(candidates) > 1 else None
    badge_label, badge_emoji, template_key = BADGES[primary.story_type]
    interesting_score = calculate_interesting_score(game, metrics, candidates)
    headline = _daily_activity_headline(game) if primary.story_type == "daily_activity" else _headline(primary.story_type, primary.confidence)

    return GameStory(
        primary_story=primary.story_type,
        secondary_story=secondary.story_type if secondary else None,
        badge_label=badge_label,
        badge_emoji=badge_emoji,
        headline=headline,
        subheadline=_subheadline(game, metrics),
        key_move_number=_key_move_number(primary.story_type, metrics),
        key_position_fen=_key_position_fen(primary.story_type, game, metrics),
        key_move_san=_key_move_san(primary.story_type, metrics),
        template_key=template_key,
        interesting_score=interesting_score,
        confidence_score=round(primary.confidence, 2),
        reasons=list(dict.fromkeys([*primary.reasons, *(secondary.reasons if secondary else ())])),
    )


def _headline(story_type: str, confidence: float) -> str:
    if confidence < 0.75 and story_type in SOFT_HEADLINE_TEMPLATES:
        return SOFT_HEADLINE_TEMPLATES[story_type]
    return HEADLINE_TEMPLATES[story_type]


def _daily_activity_headline(game: ParsedGame) -> str:
    opening = game.opening_name
    speed = game.speed or "game"
    opponent = game.opponent_username
    if game.result == "win" and opening:
        return f"A win in the {opening} added to the journal."
    if game.result == "win":
        return f"A {game.moves_count}-move {speed} win{_against(opponent)}."
    if game.result == "loss" and opening:
        return f"A tough {opening} battle added to the journal."
    if game.result == "loss":
        return f"A {game.moves_count}-move {speed} loss{_against(opponent)}."
    if game.result == "draw" and opening:
        return f"A balanced {opening} fight added to the journal."
    if game.result == "draw":
        return f"A {game.moves_count}-move draw{_against(opponent)}."
    return f"A new {speed} game added to the chess journal."


def _against(opponent: str | None) -> str:
    return f" against {opponent}" if opponent else ""


def _subheadline(game: ParsedGame, metrics: GameMetrics | None) -> str | None:
    parts: list[str] = []
    if game.opening_name:
        parts.append(game.opening_name)
    if metrics and metrics.turning_point_move and metrics.biggest_eval_swing is not None and metrics.biggest_eval_swing >= 2.5:
        parts.append(f"The game flipped around move {metrics.turning_point_move}.")
    if game.opponent_username:
        parts.append(f"Against {game.opponent_username}.")
    return " ".join(parts) or None


def _key_position_fen(story_type: str, game: ParsedGame, metrics: GameMetrics | None) -> str | None:
    if metrics is None:
        return game.final_fen
    if story_type == "swindle":
        return metrics.lowest_eval_fen or metrics.turning_point_fen or game.final_fen
    if story_type in {"heartbreaker", "turning_point"}:
        return metrics.turning_point_fen or game.final_fen
    return game.final_fen


def _key_move_number(story_type: str, metrics: GameMetrics | None) -> int | None:
    if metrics is None or story_type not in {"swindle", "heartbreaker", "turning_point"}:
        return None
    return metrics.turning_point_move


def _key_move_san(story_type: str, metrics: GameMetrics | None) -> str | None:
    if metrics is None or story_type not in {"swindle", "heartbreaker", "turning_point"}:
        return None
    return metrics.turning_point_san
