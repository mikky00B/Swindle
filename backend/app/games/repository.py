from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_session
from app.games.analysis import analyze_game_with_cloud_eval, metrics_from_mock_user_evals
from app.games.pgn_parser import compute_final_fen_from_moves, compute_final_fen_from_pgn
from app.games.schemas import GameMetrics, ParsedGame
from app.integrations.lichess.service import ensure_local_user
from app.models import Game, GameMetric, GameStory, PublishedPost, SuggestedPost
from app.share_cards.schemas import ShareCardData, build_share_card_data
from app.story.processor import generate_story
from app.story.schemas import GameStory as StorySchema


def save_imported_game(
    *,
    user_id: str,
    chess_account_id: str,
    platform: str,
    external_game_id: str,
    raw_payload: dict[str, Any],
    parsed_game: ParsedGame,
    story: StorySchema,
    share_card: ShareCardData,
) -> tuple[bool, str]:
    with get_session() as session:
        ensure_local_user(session, user_id)
        existing = session.scalar(
            select(Game).where(
                Game.user_id == user_id,
                Game.platform == platform,
                Game.external_game_id == external_game_id,
            )
        )
        if existing:
            return False, existing.id

        game = Game(
            user_id=user_id,
            chess_account_id=chess_account_id,
            platform=platform,
            external_game_id=external_game_id,
            pgn=parsed_game.pgn,
            raw_payload=raw_payload,
            white_username=parsed_game.white_username,
            black_username=parsed_game.black_username,
            user_color=parsed_game.user_color,
            opponent_username=parsed_game.opponent_username,
            result=parsed_game.result,
            winner_color=parsed_game.winner_color,
            termination=parsed_game.termination,
            rated=parsed_game.rated,
            speed=parsed_game.speed,
            time_control=parsed_game.time_control,
            opening_name=parsed_game.opening_name,
            opening_eco=parsed_game.opening_eco,
            moves_count=parsed_game.moves_count,
            user_rating_before=parsed_game.user_rating_before,
            user_rating_after=parsed_game.user_rating_after,
            opponent_rating=parsed_game.opponent_rating,
            rating_change=parsed_game.rating_change,
            played_at=parsed_game.played_at,
            final_fen=parsed_game.final_fen,
            processing_status="processed",
        )
        session.add(game)
        session.flush()
        story_model = _story_model(game.id, user_id, share_card.story, share_card)
        session.add(story_model)
        session.flush()
        _sync_suggestion_for_story(session, story_model)
        session.add(GameMetric(game_id=game.id, analysis_source="metadata_only"))
        return True, game.id


def list_imported_games(user_id: str) -> list[dict[str, Any]]:
    with get_session() as session:
        games = (
            session.scalars(
                select(Game)
                .options(joinedload(Game.story), joinedload(Game.metrics))
                .where(Game.user_id == user_id)
                .order_by(Game.played_at.desc().nullslast(), Game.imported_at.desc())
            )
            .unique()
            .all()
        )
        return [_game_to_journal_dict(game) for game in games]


def get_imported_game_detail(game_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        game = session.scalar(
            select(Game).options(joinedload(Game.story), joinedload(Game.metrics)).where(Game.id == game_id, Game.user_id == user_id)
        )
        if game is None:
            return None
        return _game_to_detail_dict(game, session=session)


def get_game_debug(game_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        game = session.scalar(
            select(Game).options(joinedload(Game.story), joinedload(Game.metrics)).where(Game.id == game_id, Game.user_id == user_id)
        )
        if game is None:
            return None
        _ensure_final_fen(game)
        card = _card_for_game(session, game)
        return {
            "game_id": game.id,
            "external_game_id": game.external_game_id,
            "user_color": game.user_color,
            "result": game.result,
            "opponent_username": game.opponent_username,
            "opponent_rating": game.opponent_rating,
            "opening_name": game.opening_name,
            "moves_count": game.moves_count,
            "final_fen": game.final_fen,
            "key_position_fen": game.story.key_position_fen if game.story else None,
            "card_fen": card["story"]["key_position_fen"] if card else None,
            "board_position_source": card.get("board_position_source") if card else None,
            "key_move_number": game.story.key_move_number if game.story else None,
            "key_move_san": game.story.key_move_san if game.story else None,
            "story_type": game.story.primary_story if game.story else None,
            "headline": game.story.headline if game.story else None,
            "subheadline": game.story.subheadline if game.story else None,
            "metrics": _metrics_to_dict(game.metrics),
            "raw_payload": game.raw_payload,
        }


def get_share_card(game_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        game = session.scalar(
            select(Game).options(joinedload(Game.story), joinedload(Game.metrics)).where(Game.id == game_id, Game.user_id == user_id)
        )
        return _card_for_game(session, game)


def _card_for_game(session, game: Game | None) -> dict[str, Any] | None:
    if game is None or game.story is None:
        return None
    _ensure_final_fen(game)
    if _share_card_needs_rebuild(game.story.share_card_data, game):
        parsed = _parsed_from_game(game)
        metrics = _metrics_from_model(game.metrics)
        story_schema = StorySchema.model_validate(_story_to_dict(game.story))
        share_card = build_share_card_data(parsed, story_schema, metrics, _player_username(game))
        _update_story_model(game.story, share_card.story, share_card)
        session.flush()
        return share_card.model_dump(mode="json")
    return game.story.share_card_data


def reprocess_game(game_id: str, user_id: str, *, with_eval: bool = False) -> dict[str, Any] | None:
    with get_session() as session:
        game = session.scalar(
            select(Game).options(joinedload(Game.story), joinedload(Game.metrics)).where(Game.id == game_id, Game.user_id == user_id)
        )
        if game is None:
            return None

        _ensure_final_fen(game)
        parsed = _parsed_from_game(game)
        metrics = analyze_game_with_cloud_eval(parsed, session) if with_eval else _metrics_from_model(game.metrics)
        story = generate_story(parsed, metrics)
        share_card = build_share_card_data(parsed, story, metrics, _player_username(game))

        if with_eval:
            if game.metrics is None:
                game.metrics = GameMetric(game_id=game.id)
                session.flush()
            _update_metric_model(game.metrics, metrics)

        if game.story is None:
            game.story = _story_model(game.id, user_id, share_card.story, share_card)
            session.flush()
        else:
            _update_story_model(game.story, share_card.story, share_card)
        game.processing_status = "processed"
        game.updated_at = datetime.now(timezone.utc)
        _sync_suggestion_for_story(session, game.story)
        _sync_published_post_for_story(session, game.story)
        session.flush()
        return _game_to_detail_dict(game, session=session)


def debug_eval_game(game_id: str, user_id: str, eval_curve: list[Any], analysis_status: str = "complete") -> dict[str, Any] | None:
    with get_session() as session:
        game = session.scalar(
            select(Game).options(joinedload(Game.story), joinedload(Game.metrics)).where(Game.id == game_id, Game.user_id == user_id)
        )
        if game is None:
            return None
        _ensure_final_fen(game)
        parsed = _parsed_from_game(game)
        metrics = metrics_from_mock_user_evals(parsed, eval_curve, analysis_status)
        story = generate_story(parsed, metrics)
        share_card = build_share_card_data(parsed, story, metrics, _player_username(game))

        if game.metrics is None:
            game.metrics = GameMetric(game_id=game.id)
            session.flush()
        _update_metric_model(game.metrics, metrics)

        if game.story is None:
            game.story = _story_model(game.id, user_id, share_card.story, share_card)
            session.flush()
        else:
            _update_story_model(game.story, share_card.story, share_card)
        game.processing_status = "processed"
        game.updated_at = datetime.now(timezone.utc)
        _sync_suggestion_for_story(session, game.story)
        _sync_published_post_for_story(session, game.story)
        session.flush()
        return _game_to_detail_dict(game, session=session)


def reprocess_all_games(user_id: str) -> dict[str, int]:
    with get_session() as session:
        ids = session.scalars(select(Game.id).where(Game.user_id == user_id)).all()
    processed = 0
    for game_id in ids:
        if reprocess_game(game_id, user_id) is not None:
            processed += 1
    return {"processed": processed}


def list_suggested_stories(user_id: str) -> list[dict[str, Any]]:
    with get_session() as session:
        _ensure_missing_suggestions(session, user_id)
        suggestions = (
            session.scalars(
                select(SuggestedPost)
                .join(Game, SuggestedPost.game_id == Game.id)
                .where(SuggestedPost.user_id == user_id, SuggestedPost.status == "suggested")
                .order_by(Game.played_at.desc().nullslast(), SuggestedPost.created_at.desc())
            )
            .unique()
            .all()
        )
        result: list[dict[str, Any]] = []
        for suggestion in suggestions:
            game = session.scalar(
                select(Game)
                .options(joinedload(Game.story), joinedload(Game.metrics))
                .where(Game.id == suggestion.game_id, Game.user_id == user_id)
            )
            if game is None or game.story is None:
                continue
            item = _game_to_journal_dict(game)
            item["suggestion_id"] = suggestion.id
            item["suggestion_status"] = suggestion.status
            result.append(item)
        return result


def ignore_suggested_story(story_id: str, user_id: str) -> dict[str, Any] | None:
    with get_session() as session:
        story = session.scalar(select(GameStory).where(GameStory.id == story_id, GameStory.user_id == user_id))
        if story is None:
            return None
        suggestion = _get_suggestion_for_story(session, story)
        if suggestion is None:
            suggestion = SuggestedPost(user_id=user_id, game_id=story.game_id, game_story_id=story.id)
            session.add(suggestion)
        suggestion.status = "ignored"
        suggestion.updated_at = datetime.now(timezone.utc)
        return {"ignored": True, "story_id": story.id}


def reset_ignored_suggestions(user_id: str) -> dict[str, int]:
    with get_session() as session:
        _ensure_missing_suggestions(session, user_id)
        suggestions = session.scalars(
            select(SuggestedPost).where(SuggestedPost.user_id == user_id, SuggestedPost.status == "ignored")
        ).all()
        restored = 0
        for suggestion in suggestions:
            story = session.get(GameStory, suggestion.game_story_id)
            if story is None or not _story_is_suggestable(story):
                continue
            suggestion.status = "suggested"
            suggestion.updated_at = datetime.now(timezone.utc)
            restored += 1
        return {"restored": restored}


def _story_model(game_id: str, user_id: str, story: StorySchema, share_card: ShareCardData) -> GameStory:
    return GameStory(
        game_id=game_id,
        user_id=user_id,
        primary_story=story.primary_story,
        secondary_story=story.secondary_story,
        badge_label=story.badge_label,
        badge_emoji=story.badge_emoji,
        headline=story.headline,
        subheadline=story.subheadline,
        caption=story.caption,
        mood=story.mood,
        key_move_number=story.key_move_number,
        key_position_fen=story.key_position_fen,
        key_move_san=story.key_move_san,
        key_move_from=story.key_move_from,
        key_move_to=story.key_move_to,
        template_key=story.template_key,
        interesting_score=story.interesting_score,
        confidence_score=story.confidence_score,
        reasons=story.reasons,
        share_card_data=share_card.model_dump(mode="json"),
    )


def _update_story_model(model: GameStory, story: StorySchema, share_card: ShareCardData) -> None:
    for field, value in story.model_dump(mode="json").items():
        setattr(model, field, value)
    model.share_card_data = share_card.model_dump(mode="json")
    model.updated_at = datetime.now(timezone.utc)


def _game_to_journal_dict(game: Game) -> dict[str, Any]:
    return {
        "id": game.id,
        "external_game_id": game.external_game_id,
        "platform": game.platform,
        "white_username": game.white_username,
        "black_username": game.black_username,
        "user_color": game.user_color,
        "opponent_username": game.opponent_username,
        "result": game.result,
        "speed": game.speed,
        "time_control": game.time_control,
        "opening_name": game.opening_name,
        "opening_eco": game.opening_eco,
        "moves_count": game.moves_count,
        "user_rating_before": game.user_rating_before,
        "opponent_rating": game.opponent_rating,
        "rating_change": game.rating_change,
        "played_at": _iso(game.played_at),
        "final_fen": game.final_fen,
        "imported_at": _iso(game.imported_at),
        "processing_status": game.processing_status,
        "story": _story_to_dict(game.story),
        "metrics": _metrics_to_dict(game.metrics),
    }


def _game_to_detail_dict(game: Game, *, session=None) -> dict[str, Any]:
    item = _game_to_journal_dict(game)
    item["raw_payload"] = game.raw_payload
    if session is not None and game.story is not None:
        post = session.scalar(
            select(PublishedPost).where(
                PublishedPost.user_id == game.user_id,
                PublishedPost.game_story_id == game.story.id,
                PublishedPost.visibility == "public",
            )
        )
        item["published_post"] = _published_post_summary(post)
    return item


def _story_to_dict(story: GameStory | None) -> dict[str, Any] | None:
    if story is None:
        return None
    return {
        "id": story.id,
        "primary_story": story.primary_story,
        "secondary_story": story.secondary_story,
        "badge_label": story.badge_label,
        "badge_emoji": story.badge_emoji,
        "headline": story.headline,
        "subheadline": story.subheadline,
        "caption": story.caption,
        "mood": story.mood,
        "key_move_number": story.key_move_number,
        "key_position_fen": story.key_position_fen,
        "key_move_san": story.key_move_san,
        "key_move_from": story.key_move_from,
        "key_move_to": story.key_move_to,
        "template_key": story.template_key,
        "interesting_score": story.interesting_score,
        "confidence_score": story.confidence_score,
        "reasons": story.reasons or [],
    }


def _metrics_to_dict(metric: GameMetric | None) -> dict[str, Any]:
    if metric is None:
        return {"analysis_source": "metadata_only", "analysis_status": "none", "eval_points": 0}
    return {
        "accuracy": metric.accuracy,
        "lowest_eval": metric.lowest_eval,
        "highest_eval": metric.highest_eval,
        "biggest_eval_swing": metric.biggest_eval_swing,
        "turning_point_move": metric.turning_point_move,
        "turning_point_fen": metric.turning_point_fen,
        "turning_point_san": metric.turning_point_san,
        "analysis_depth": metric.analysis_depth,
        "analysis_source": metric.analysis_source,
        "analysis_status": metric.analysis_status,
        "eval_points": len(metric.eval_curve or []),
    }


SUGGESTED_STORY_TYPES = {
    "giant_slayer",
    "miniature",
    "long_grind",
    "rating_milestone",
    "swindle",
    "heartbreaker",
    "turning_point",
}


def _story_is_suggestable(story: GameStory) -> bool:
    return story.interesting_score >= 0.75 or story.primary_story in SUGGESTED_STORY_TYPES


def _get_suggestion_for_story(session, story: GameStory) -> SuggestedPost | None:
    return session.scalar(
        select(SuggestedPost).where(SuggestedPost.user_id == story.user_id, SuggestedPost.game_story_id == story.id)
    )


def _sync_suggestion_for_story(session, story: GameStory | None) -> None:
    if story is None:
        return
    suggestion = _get_suggestion_for_story(session, story)
    if not _story_is_suggestable(story):
        if suggestion and suggestion.status == "suggested":
            suggestion.status = "ignored"
            suggestion.updated_at = datetime.now(timezone.utc)
        return
    if suggestion is None:
        session.add(SuggestedPost(user_id=story.user_id, game_id=story.game_id, game_story_id=story.id))


def _sync_published_post_for_story(session, story: GameStory | None) -> None:
    if story is None:
        return
    post = session.scalar(
        select(PublishedPost).where(
            PublishedPost.user_id == story.user_id,
            PublishedPost.game_story_id == story.id,
            PublishedPost.visibility == "public",
        )
    )
    if post is None:
        return
    post.headline = story.headline
    post.caption = story.caption
    post.updated_at = datetime.now(timezone.utc)


def _published_post_summary(post: PublishedPost | None) -> dict[str, Any] | None:
    if post is None:
        return None
    return {
        "id": post.id,
        "game_id": post.game_id,
        "game_story_id": post.game_story_id,
        "headline": post.headline,
        "caption": post.caption,
        "visibility": post.visibility,
        "created_at": _iso(post.created_at),
        "updated_at": _iso(post.updated_at),
    }


def _ensure_missing_suggestions(session, user_id: str) -> None:
    stories = session.scalars(select(GameStory).where(GameStory.user_id == user_id)).all()
    for story in stories:
        _sync_suggestion_for_story(session, story)
    session.flush()


def _parsed_from_game(game: Game) -> ParsedGame:
    final_fen = game.final_fen or _compute_final_fen_for_game(game)
    return ParsedGame(
        pgn=game.pgn,
        white_username=game.white_username,
        black_username=game.black_username,
        user_color=game.user_color,
        opponent_username=game.opponent_username,
        result=game.result,
        winner_color=game.winner_color,
        termination=game.termination,
        rated=game.rated,
        speed=game.speed,
        time_control=game.time_control,
        opening_name=game.opening_name,
        opening_eco=game.opening_eco,
        moves_count=game.moves_count,
        user_rating_before=game.user_rating_before,
        user_rating_after=game.user_rating_after,
        opponent_rating=game.opponent_rating,
        rating_change=game.rating_change,
        played_at=game.played_at,
        final_fen=final_fen,
    )


def _metrics_from_model(metric: GameMetric | None) -> GameMetrics | None:
    if metric is None:
        return None
    return GameMetrics(
        accuracy=metric.accuracy,
        lowest_eval=metric.lowest_eval,
        highest_eval=metric.highest_eval,
        biggest_eval_swing=metric.biggest_eval_swing,
        turning_point_move=metric.turning_point_move,
        turning_point_fen=metric.turning_point_fen,
        turning_point_san=metric.turning_point_san,
        lowest_eval_fen=metric.lowest_eval_fen,
        highest_eval_fen=metric.highest_eval_fen,
        blunders_count=metric.blunders_count,
        mistakes_count=metric.mistakes_count,
        inaccuracies_count=metric.inaccuracies_count,
        captures_count=metric.captures_count,
        checks_count=metric.checks_count,
        user_lowest_clock_seconds=metric.user_lowest_clock_seconds,
        moves_under_time_pressure=metric.moves_under_time_pressure,
        eval_curve=metric.eval_curve,
        analysis_depth=metric.analysis_depth,
        analysis_source=metric.analysis_source,
        analysis_status=metric.analysis_status,
    )


def _update_metric_model(model: GameMetric, metrics: GameMetrics) -> None:
    model.accuracy = metrics.accuracy
    model.lowest_eval = metrics.lowest_eval
    model.highest_eval = metrics.highest_eval
    model.biggest_eval_swing = metrics.biggest_eval_swing
    model.turning_point_move = metrics.turning_point_move
    model.turning_point_fen = metrics.turning_point_fen
    model.turning_point_san = metrics.turning_point_san
    model.lowest_eval_fen = metrics.lowest_eval_fen
    model.highest_eval_fen = metrics.highest_eval_fen
    model.eval_curve = metrics.eval_curve
    model.analysis_depth = metrics.analysis_depth
    model.analysis_source = metrics.analysis_source
    model.analysis_status = metrics.analysis_status
    model.updated_at = datetime.now(timezone.utc)


def _player_username(game: Game) -> str:
    if game.user_color == "white" and game.white_username:
        return game.white_username
    if game.user_color == "black" and game.black_username:
        return game.black_username
    return "Player"


def _share_card_needs_rebuild(data: dict[str, Any], model: Game) -> bool:
    if not data:
        return True
    if "board_position_source" not in data:
        return True
    game = data.get("game")
    if not isinstance(game, dict) or "user_color" not in game or "final_fen" not in game:
        return True
    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or "eval_points" not in metrics or "analysis_status" not in metrics:
        return True
    if game.get("final_fen") != model.final_fen:
        return True
    return data.get("board_position_source") == "fallback_starting_position" and model.final_fen is not None


def _ensure_final_fen(game: Game) -> None:
    if game.final_fen:
        return
    game.final_fen = _compute_final_fen_for_game(game)
    if game.final_fen:
        game.updated_at = datetime.now(timezone.utc)


def _compute_final_fen_for_game(game: Game) -> str | None:
    raw_moves = game.raw_payload.get("moves") if isinstance(game.raw_payload, dict) else None
    if isinstance(raw_moves, str):
        final_fen = compute_final_fen_from_moves(raw_moves)
        if final_fen:
            return final_fen
    return compute_final_fen_from_pgn(game.pgn)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
