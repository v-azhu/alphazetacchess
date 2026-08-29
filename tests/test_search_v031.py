from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


def _move_signature(move):
    return (move.from_pos, move.to_pos)


def test_iterative_deepening_reaches_requested_depth():
    result = SearchEngine(depth=2).choose_move(Board(), Color.RED)

    assert result.best_move is not None
    assert result.depth == 2
    assert result.nodes_evaluated > 0


def test_iterative_deepening_matches_fixed_depth():
    board = Board()

    iterative = SearchEngine(
        depth=2,
        iterative_deepening=True,
    )
    fixed = SearchEngine(
        depth=2,
        iterative_deepening=False,
    )

    iterative_result = iterative.choose_move(board, Color.RED)
    fixed_result = fixed.choose_move(board, Color.RED)

    # Both searches must reach the same minimax value.
    assert iterative_result.score == fixed_result.score

    # Move objects are currently compared by identity rather than by
    # from/to coordinates, so compare their actual chess moves.
    assert _move_signature(iterative_result.best_move) ==         _move_signature(fixed_result.best_move)


def test_root_move_ordering_prefers_previous_best_move():
    board = Board()
    engine = SearchEngine(depth=1)

    from alphazetacchess.core.rule import Rule

    moves = Rule.generate_legal_moves(board, Color.RED)
    preferred = moves[-1]

    ordered = engine._order_root_moves(moves, preferred)

    assert ordered[0] is preferred
