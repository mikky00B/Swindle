from app.games.schemas import GameMetrics, ParsedGame
from app.story.processor import generate_story


def test_giant_slayer_story_wins_priority_over_miniature() -> None:
    game = ParsedGame(
        pgn="",
        result="win",
        moves_count=20,
        user_rating_before=1200,
        opponent_rating=1400,
    )

    story = generate_story(game)

    assert story.primary_story == "giant_slayer"
    assert story.secondary_story == "miniature"
    assert story.interesting_score >= 0.75


def test_swindle_uses_eval_data() -> None:
    game = ParsedGame(pgn="", result="win", moves_count=48)
    metrics = GameMetrics(lowest_eval=-5.2, biggest_eval_swing=7.4, eval_curve=[0, -5.2, 2.2])

    story = generate_story(game, metrics)

    assert story.primary_story == "swindle"
    assert story.badge_label == "The Swindle"
    assert story.confidence_score == 0.95


def test_quiet_game_stays_journal_entry() -> None:
    game = ParsedGame(pgn="", result="draw", moves_count=38)

    story = generate_story(game)

    assert story.primary_story == "daily_activity"
    assert story.interesting_score < 0.75


def test_daily_game_headline_uses_result_and_opening_metadata() -> None:
    game = ParsedGame(pgn="", result="loss", moves_count=38, opening_name="French Defense")

    story = generate_story(game)

    assert story.primary_story == "daily_activity"
    assert story.headline == "A tough French Defense battle added to the journal."


def test_no_eval_data_does_not_generate_engine_story() -> None:
    game = ParsedGame(pgn="", result="win", moves_count=48)

    story = generate_story(game)

    assert story.primary_story == "daily_activity"


def test_daily_game_win_headline() -> None:
    game = ParsedGame(pgn="", result="win", moves_count=28, speed="blitz", opponent_username="Bai_Daniil")

    story = generate_story(game)

    assert story.headline == "A 28-move blitz win against Bai_Daniil."


def test_daily_game_loss_headline() -> None:
    game = ParsedGame(pgn="", result="loss", moves_count=44, speed="rapid", opponent_username="Bai_Daniil")

    story = generate_story(game)

    assert story.headline == "A 44-move rapid loss against Bai_Daniil."


def test_daily_game_draw_headline() -> None:
    game = ParsedGame(pgn="", result="draw", moves_count=36, opponent_username="Bai_Daniil")

    story = generate_story(game)

    assert story.headline == "A 36-move draw against Bai_Daniil."
