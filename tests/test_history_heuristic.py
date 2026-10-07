from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.history_heuristic import HistoryHeuristic


def test_history_rewards_quiet_move():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    assert history.get(move) == 0
    history.reward(move, 3)
    assert history.get(move) > 0


def test_history_penalizes_quiet_move():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    history.penalize(move, 3)
    assert history.get(move) < 0


def test_history_ignores_captures():
    class Piece:
        type = "pawn"

    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = Piece()

    history = HistoryHeuristic()
    move = Move()
    history.reward(move, 5)
    assert history.get(move) == 0


def test_history_stays_bounded():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    for _ in range(1000):
        history.reward(move, 20)
    assert history.get(move) <= history.MAX_SCORE


def test_history_scores_are_separate_for_each_side():
    red_move = Move((0, 0), (0, 1))
    red_move.moved_piece = Piece(PieceType.ROOK, Color.RED, 0, 0)
    black_move = Move((0, 0), (0, 1))
    black_move.moved_piece = Piece(PieceType.ROOK, Color.BLACK, 0, 0)

    history = HistoryHeuristic()
    history.reward(red_move, 3)

    assert history.get(red_move) > 0
    assert history.get(black_move) == 0

    history.penalize(black_move, 3)
    assert history.get(red_move) > 0
    assert history.get(black_move) < 0


def test_history_lookup_ignores_captures_matching_a_scored_quiet_move():
    quiet_move = Move((0, 0), (0, 1))
    quiet_move.moved_piece = Piece(PieceType.ROOK, Color.RED, 0, 0)
    capture_move = Move((0, 0), (0, 1))
    capture_move.moved_piece = Piece(PieceType.ROOK, Color.RED, 0, 0)
    capture_move.captured_piece = Piece(PieceType.PAWN, Color.BLACK, 0, 1)

    history = HistoryHeuristic()
    history.reward(quiet_move, 4)

    assert history.get(quiet_move) > 0
    assert history.get(capture_move) == 0
