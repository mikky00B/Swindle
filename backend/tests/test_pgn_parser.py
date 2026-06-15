from app.games.pgn_parser import compute_final_fen_from_moves, parse_pgn

from tests.test_prototype_api import SAMPLE_PGN


def test_parse_pgn_extracts_user_context() -> None:
    game = parse_pgn(SAMPLE_PGN, "clevermike")

    assert game.white_username == "clevermike"
    assert game.black_username == "higherRated"
    assert game.user_color == "white"
    assert game.opponent_username == "higherRated"
    assert game.result == "win"
    assert game.winner_color == "white"
    assert game.user_rating_before == 1392
    assert game.opponent_rating == 1560
    assert game.opening_name == "Sicilian Defense"
    assert game.moves_count == 31
    assert game.final_fen


def test_compute_final_fen_from_lichess_moves() -> None:
    fen = compute_final_fen_from_moves("e4 e5 Nf3 Nc6 Bb5 a6 1-0")

    assert fen == "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4"


def test_compute_final_fen_from_invalid_moves_returns_none() -> None:
    assert compute_final_fen_from_moves("e4 definitely-not-a-move") is None
