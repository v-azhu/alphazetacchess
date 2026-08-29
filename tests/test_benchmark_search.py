from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


def _move_signature(move):
    if move is None:
        return None

    return (
        move.from_pos,
        move.to_pos,
    )


def test_benchmark_baseline_position():
    board = Board()

    fixed = SearchEngine(
        depth=1,
        iterative_deepening=False,
    )

    iterative = SearchEngine(
        depth=1,
        iterative_deepening=True,
    )

    fixed_result = fixed.choose_move(board, Color.RED)
    iterative_result = iterative.choose_move(board, Color.RED)

    assert fixed_result.score == iterative_result.score

    assert _move_signature(
        fixed_result.best_move
    ) == _move_signature(
        iterative_result.best_move
    )


def test_benchmark_search_returns_valid_result():
    board = Board()

    engine = SearchEngine(
        depth=1,
        iterative_deepening=True,
    )

    result = engine.choose_move(
        board,
        Color.RED,
    )

    assert result.best_move is not None
    assert result.depth == 1
    assert result.nodes_evaluated > 0