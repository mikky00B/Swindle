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


def test_find_move_squares_returns_origin_and_destination() -> None:
    from app.games.pgn_parser import find_move_squares

    moves = "e4 c5 Nf3 d6 d4 cxd4"

    assert find_move_squares(moves, 1, "e4") == ("e2", "e4")
    assert find_move_squares(moves, 2, "Nf3") == ("g1", "f3")
    assert find_move_squares(moves, 3, "cxd4") == ("c5", "d4")
    assert find_move_squares(moves, 9, "e4") is None


def test_extract_clock_metrics_uses_user_color_clocks() -> None:
    from app.games.clocks import extract_clock_metrics

    # Centiseconds remaining after each ply: white, black, white, black...
    payload = {"clocks": [18000, 17500, 12000, 900, 300, 15000]}
    assert extract_clock_metrics(payload, "white") == (3, 1)
    assert extract_clock_metrics(payload, "black") == (9, 1)
    assert extract_clock_metrics(payload, None) == (None, None)
    assert extract_clock_metrics({}, "white") == (None, None)
