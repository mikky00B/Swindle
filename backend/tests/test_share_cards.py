from app.games.schemas import ParsedGame
from app.share_cards.schemas import STARTING_FEN, build_share_card_data
from app.story.schemas import GameStory


def test_invalid_key_fen_falls_back_to_final_position() -> None:
    game = ParsedGame(
        pgn="",
        result="win",
        moves_count=12,
        final_fen="8/8/8/8/8/8/4k3/4K3 w - - 0 1",
    )
    story = base_story(key_position_fen="not-a-fen", key_move_number=4)

    card = build_share_card_data(game, story, None, "player")

    assert card.board_position_source == "final_position"
    assert card.story.key_position_fen == game.final_fen


def test_invalid_key_and_final_fen_fall_back_to_starting_position() -> None:
    game = ParsedGame(pgn="", result="win", moves_count=12, final_fen="bad-final")
    story = base_story(key_position_fen="bad-key", key_move_number=4)

    card = build_share_card_data(game, story, None, "player")

    assert card.board_position_source == "fallback_starting_position"
    assert card.story.key_position_fen == STARTING_FEN


def test_valid_key_fen_is_labeled_key_position() -> None:
    key_fen = "8/8/8/8/8/8/4k3/4K3 b - - 0 1"
    game = ParsedGame(pgn="", result="win", moves_count=12, final_fen=STARTING_FEN, user_color="black")
    story = base_story(key_position_fen=key_fen, key_move_number=4)

    card = build_share_card_data(game, story, None, "player")

    assert card.board_position_source == "key_position"
    assert card.story.key_position_fen == key_fen
    assert card.game.user_color == "black"
    assert card.game.final_fen == STARTING_FEN


def base_story(key_position_fen: str, key_move_number: int | None) -> GameStory:
    return GameStory(
        primary_story="daily_activity",
        badge_label="Daily Game",
        badge_emoji="DG",
        headline="Another game added to the chess journal.",
        key_move_number=key_move_number,
        key_position_fen=key_position_fen,
        template_key="generic_square_v1",
        interesting_score=0.1,
        confidence_score=0.75,
        reasons=["journal_entry"],
    )
