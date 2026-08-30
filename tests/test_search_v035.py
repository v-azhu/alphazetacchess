"""V0.3.5 search stability and regression tests."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine


def signature(move):
    return None if move is None else (move.from_pos, move.to_pos)


def test_search_returns_a_legal_move():
    board = Board()
    result = SearchEngine(depth=2).choose_move(board, Color.RED)
    legal = Rule.generate_legal_moves(board, Color.RED)
    assert result.best_move is not None
    assert signature(result.best_move) in {signature(m) for m in legal}


def test_fresh_search_is_deterministic():
    board = Board()
    a = SearchEngine(depth=2).choose_move(board, Color.RED)
    b = SearchEngine(depth=2).choose_move(board, Color.RED)
    assert a.score == b.score
    assert signature(a.best_move) == signature(b.best_move)


def test_pvs_preserves_minimax_score():
    board = Board()
    pvs = SearchEngine(
        depth=2, iterative_deepening=False,
        use_transposition_table=False, use_pvs=True,
        use_quiescence=False
    ).choose_move(board, Color.RED)
    plain = SearchEngine(
        depth=2, iterative_deepening=False,
        use_transposition_table=False, use_pvs=False,
        use_quiescence=False
    ).choose_move(board, Color.RED)
    assert pvs.score == plain.score


def test_tt_preserves_minimax_score():
    board = Board()
    with_tt = SearchEngine(
        depth=2, iterative_deepening=False,
        use_transposition_table=True, use_pvs=False,
        use_quiescence=False
    ).choose_move(board, Color.RED)
    without_tt = SearchEngine(
        depth=2, iterative_deepening=False,
        use_transposition_table=False, use_pvs=False,
        use_quiescence=False
    ).choose_move(board, Color.RED)
    assert with_tt.score == without_tt.score


def test_quiescence_search_returns_a_legal_move():
    board = Board()
    result = SearchEngine(depth=2, use_quiescence=True).choose_move(board, Color.RED)
    legal = Rule.generate_legal_moves(board, Color.RED)
    assert result.best_move is not None
    assert signature(result.best_move) in {signature(m) for m in legal}
