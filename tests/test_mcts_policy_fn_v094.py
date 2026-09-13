"""V0.9.4 tests for engine/mcts.py's policy_fn parameter -- an optional
pluggable policy source (e.g. NeuralPolicyEvaluator), taking priority
over use_heuristic_priors when both are set.
"""
import math

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.mcts import MCTSEngine, _MCTSNode


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def hanging_rook_board():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 4)
    put(board, PieceType.ROOK, Color.BLACK, 0, 5)
    return board


def test_expand_and_evaluate_uses_policy_fn_when_provided():
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    node = _MCTSNode(prior=1.0)

    calls = []

    def fake_policy_fn(b, color, moves):
        calls.append((color, tuple(moves)))
        n = len(moves)
        return {m: 1.0 / n for m in moves}

    engine = MCTSEngine(policy_fn=fake_policy_fn)
    engine._expand_and_evaluate(board, Color.RED, node)

    assert len(calls) == 1
    called_color, called_moves = calls[0]
    assert called_color == Color.RED
    # Move has no __eq__/__hash__ override (identity semantics), so
    # compare by (from_pos, to_pos) pairs rather than set equality on
    # the objects themselves -- legal_moves here is a second, separate
    # Rule.generate_legal_moves() call and will never be the same
    # object instances as the ones _expand_and_evaluate generated
    # internally, even for the "same" logical moves.
    called_pairs = {(m.from_pos, m.to_pos) for m in called_moves}
    legal_pairs = {(m.from_pos, m.to_pos) for m in legal_moves}
    assert called_pairs == legal_pairs
    n = len(legal_moves)
    assert all(math.isclose(child.prior, 1.0 / n) for child in node.children.values())


def test_policy_fn_takes_priority_over_use_heuristic_priors():
    board = hanging_rook_board()
    node = _MCTSNode(prior=1.0)

    # A policy_fn that returns a very different distribution than
    # _heuristic_priors would (heavily favors a quiet move, not the
    # winning capture) -- if use_heuristic_priors were winning the
    # priority contest, the capture would end up with the highest
    # prior instead, since the fixture's whole point is that the
    # capture is heuristically dominant. Built dynamically from the
    # `moves` argument at call time -- Move has no __eq__/__hash__
    # override, so a dict keyed by moves from a separate
    # Rule.generate_legal_moves() call would never match up with
    # _expand_and_evaluate's own internally-generated move objects.
    def fixed_policy_fn(b, color, moves):
        quiet_move = next(m for m in moves if m.to_pos != (0, 5))
        n = len(moves)
        return {m: (0.9 if m is quiet_move else 0.1 / (n - 1)) for m in moves}

    engine = MCTSEngine(use_heuristic_priors=True, policy_fn=fixed_policy_fn)
    engine._expand_and_evaluate(board, Color.RED, node)

    quiet_children_priors = [
        child.prior for move, child in node.children.items() if move.to_pos != (0, 5)
    ]
    assert any(math.isclose(p, 0.9) for p in quiet_children_priors)


def test_choose_move_still_works_end_to_end_with_policy_fn():
    board = hanging_rook_board()

    def uniform_policy_fn(b, color, moves):
        n = len(moves)
        return {m: 1.0 / n for m in moves}

    engine = MCTSEngine(simulations=50, policy_fn=uniform_policy_fn)
    result = engine.choose_move(board, Color.RED)

    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    legal_pairs = {(m.from_pos, m.to_pos) for m in legal_moves}
    assert (result.best_move.from_pos, result.best_move.to_pos) in legal_pairs
