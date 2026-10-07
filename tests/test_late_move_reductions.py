from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.transposition_table import MATE_SCORE


def _signature(move):
    return None if move is None else (move.from_pos, move.to_pos)


def test_late_move_reductions_are_disabled_by_default():
    engine = SearchEngine(depth=4)

    assert engine.use_late_move_reductions is False
    assert engine.late_move_reductions == 0


def test_late_move_reductions_preserve_shallow_search_results():
    for board in (Board(), board_from_fen(
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    )):
        baseline = SearchEngine(depth=3, use_late_move_reductions=False)
        reduced = SearchEngine(depth=3, use_late_move_reductions=True)

        baseline_result = baseline.choose_move(board, board.current_player)
        reduced_result = reduced.choose_move(board, board.current_player)

        assert reduced_result.score == baseline_result.score
        assert _signature(reduced_result.best_move) == _signature(baseline_result.best_move)


def test_late_move_reductions_reduce_later_quiet_moves_at_depth_four():
    board = Board()
    baseline = SearchEngine(depth=4, use_late_move_reductions=False)
    reduced = SearchEngine(depth=4, use_late_move_reductions=True)

    baseline_result = baseline.choose_move(board, Color.RED)
    reduced_result = reduced.choose_move(board, Color.RED)

    assert reduced.late_move_reductions > 0
    assert reduced.late_move_researches >= 0
    assert reduced_result.score == baseline_result.score
    assert _signature(reduced_result.best_move) == _signature(baseline_result.best_move)
    assert reduced_result.nodes_evaluated < baseline_result.nodes_evaluated


def test_conservative_late_move_reductions_preserve_depth_five_central_result():
    board = board_from_fen(
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/4P4/P1P3P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    )
    for move in (
        ((1, 0), (2, 2)),
        ((1, 9), (2, 7)),
        ((7, 0), (6, 2)),
        ((7, 9), (6, 7)),
        ((1, 2), (1, 4)),
        ((7, 7), (7, 5)),
    ):
        board.move(*move)

    baseline = SearchEngine(depth=5, use_late_move_reductions=False)
    reduced = SearchEngine(depth=5, use_late_move_reductions=True)
    baseline_result = baseline.choose_move(board, board.current_player)
    reduced_result = reduced.choose_move(board, board.current_player)

    assert reduced_result.score == baseline_result.score
    assert _signature(reduced_result.best_move) == _signature(baseline_result.best_move)
    assert reduced.late_move_reductions > 0
    assert reduced.late_move_researches > 0
    assert reduced_result.nodes_evaluated < baseline_result.nodes_evaluated


def test_late_move_reductions_preserve_forced_mate_and_safe_capture():
    mate_board = board_from_fen("3aka3/4b4/9/p4N3/9/9/9/9/9/4K4 w - - 0 1")
    mate = SearchEngine(depth=4, use_late_move_reductions=True).choose_move(
        mate_board, Color.RED
    )
    assert mate.score == MATE_SCORE - 1
    assert (mate.best_move.from_pos, mate.best_move.to_pos) == ((5, 6), (6, 8))
    mate_board.move(mate.best_move.from_pos, mate.best_move.to_pos)
    assert Rule.is_checkmate(mate_board, Color.BLACK)

    capture_board = board_from_fen("4k4/9/9/R3n4/9/9/9/9/9/4K4 w - - 0 1")
    safe_capture = SearchEngine(
        depth=4, use_late_move_reductions=True
    ).choose_move(capture_board, Color.RED)
    assert (safe_capture.best_move.from_pos, safe_capture.best_move.to_pos) == (
        (0, 6), (4, 6)
    )
    assert safe_capture.best_move.captured_piece is not None
    assert Rule.is_legal_move(capture_board, safe_capture.best_move, Color.RED)
