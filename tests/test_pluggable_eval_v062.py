"""V0.6.2 tests for the pluggable `eval_fn` parameter added to
SearchEngine and MCTSEngine, letting a trained NeuralEvaluator (or any
`(board, color) -> float` callable) replace the heuristic evaluate()
call -- see search.py's `_evaluate` and mcts.py's
`_expand_and_evaluate` for the two call sites this threads through.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.evaluation import evaluate
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.mcts import MCTSEngine, _MCTSNode, _squash


# ---------------------------------------------------------------------------
# SearchEngine
# ---------------------------------------------------------------------------

def test_search_engine_default_eval_fn_preserves_existing_behavior():
    board = Board()
    engine = SearchEngine(eval_fn=None)

    assert engine._evaluate(board, Color.RED) == evaluate(
        board, Color.RED,
        use_piece_square_tables=engine.use_piece_square_tables,
        use_king_safety=engine.use_king_safety,
        use_mobility=engine.use_mobility,
        mobility_weight=engine.mobility_weight,
        use_pawn_structure=engine.use_pawn_structure,
        use_piece_coordination=engine.use_piece_coordination,
        use_endgame_heuristics=engine.use_endgame_heuristics,
    )


def test_search_engine_uses_provided_eval_fn_instead_of_heuristic():
    board = Board()
    calls = []

    def fake_eval(b, color):
        calls.append((b, color))
        return 12345.0

    engine = SearchEngine(eval_fn=fake_eval)

    assert engine._evaluate(board, Color.RED) == 12345.0
    assert calls == [(board, Color.RED)]


def test_search_engine_eval_fn_reaches_quiescence_leaf():
    # Mirrors the pattern test_endgame_v053.py/test_strength_comparison
    # already use for verifying a toggle actually reaches search, not
    # just the direct _evaluate() call.
    board = Board()
    engine = SearchEngine(eval_fn=lambda b, c: 777.0)

    score = engine._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score == 777.0


# ---------------------------------------------------------------------------
# MCTSEngine
# ---------------------------------------------------------------------------

def test_mcts_default_eval_fn_preserves_existing_behavior():
    board = Board()
    engine = MCTSEngine(eval_fn=None)
    node = _MCTSNode(prior=1.0)

    value = engine._expand_and_evaluate(board, Color.RED, node)

    expected_raw = evaluate(board, Color.RED, **engine.eval_kwargs)
    assert value == _squash(expected_raw, engine.value_scale)


def test_mcts_uses_provided_eval_fn_instead_of_heuristic():
    board = Board()
    calls = []

    def fake_eval(b, color):
        calls.append((b, color))
        return 300.0  # a real, un-squashed raw score

    engine = MCTSEngine(eval_fn=fake_eval, value_scale=500)
    node = _MCTSNode(prior=1.0)

    value = engine._expand_and_evaluate(board, Color.RED, node)

    assert calls == [(board, Color.RED)]
    assert value == _squash(300.0, 500)  # still squashed, same as the heuristic path


def test_mcts_eval_fn_reaches_through_choose_move():
    board = Board()
    engine = MCTSEngine(simulations=20, eval_fn=lambda b, c: 42.0)

    result = engine.choose_move(board, Color.RED)

    # every leaf evaluates to the same squashed constant, so the
    # search should still complete cleanly and return a legal move
    from alphazetacchess.core.rule import Rule
    legal_pairs = {(m.from_pos, m.to_pos) for m in Rule.generate_legal_moves(board, Color.RED)}
    assert (result.best_move.from_pos, result.best_move.to_pos) in legal_pairs
