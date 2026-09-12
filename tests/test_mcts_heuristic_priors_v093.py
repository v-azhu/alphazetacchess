"""V0.9.3 tests for engine/mcts.py's use_heuristic_priors: replaces the
uniform 1/N move prior with a one-ply-lookahead + softmax prior. See
docs/v0.9.3.md for the design and the real strength/speed tradeoff
this was measured against.
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
    """Red to move; one legal capture wins Black's undefended Rook,
    the rest are quiet king shuffles. A heuristic prior worth its name
    should rate the capture far above the quiet moves. Kings placed on
    different files deliberately -- same file would violate the
    flying-generals rule and filter out most moves including the
    capture this fixture exists to test."""
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 4)
    put(board, PieceType.ROOK, Color.BLACK, 0, 5)  # undefended, one file up
    return board


def test_default_expansion_reproduces_uniform_priors_exactly():
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    node = _MCTSNode(prior=1.0)

    engine = MCTSEngine(use_heuristic_priors=False)
    engine._expand_and_evaluate(board, Color.RED, node)

    n = len(legal_moves)
    assert len(node.children) == n
    assert all(math.isclose(child.prior, 1.0 / n) for child in node.children.values())


def test_heuristic_priors_rate_the_winning_capture_far_above_quiet_moves():
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    engine = MCTSEngine(use_heuristic_priors=True)
    priors = engine._heuristic_priors(board, Color.RED, legal_moves)

    capture = next(move for move in legal_moves if move.to_pos == (0, 5))
    capture_prior = priors[capture]
    other_priors = [p for move, p in priors.items() if move != capture]

    assert capture_prior > max(other_priors)
    # Not just "highest of a flat pack" -- meaningfully peaked, since a
    # free Rook is a large evaluate() swing relative to prior_temperature.
    assert capture_prior > 2 * max(other_priors)


def test_heuristic_priors_form_a_valid_probability_distribution():
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    engine = MCTSEngine(use_heuristic_priors=True)
    priors = engine._heuristic_priors(board, Color.RED, legal_moves)

    assert all(p > 0 for p in priors.values())
    assert math.isclose(sum(priors.values()), 1.0, rel_tol=1e-9)


def test_heuristic_priors_do_not_mutate_the_board():
    from alphazetacchess.core.fen import board_to_fen

    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    original_fen = board_to_fen(board)
    original_hash = board.zobrist_hash

    engine = MCTSEngine(use_heuristic_priors=True)
    engine._heuristic_priors(board, Color.RED, legal_moves)

    assert board_to_fen(board) == original_fen
    assert board.zobrist_hash == original_hash


def test_heuristic_priors_respect_eval_fn_override():
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    calls = []

    def fake_eval_fn(b, color):
        calls.append(color)
        return 0.0

    engine = MCTSEngine(use_heuristic_priors=True, eval_fn=fake_eval_fn)
    priors = engine._heuristic_priors(board, Color.RED, legal_moves)

    assert len(calls) == len(legal_moves)
    assert all(color == Color.RED for color in calls)
    # eval_fn always returned the same value for every move, so the
    # softmax must degrade to uniform -- confirms the override is
    # actually being read, not silently falling back to evaluate().
    uniform = 1.0 / len(legal_moves)
    assert all(math.isclose(p, uniform) for p in priors.values())


def test_expand_and_evaluate_uses_heuristic_priors_when_enabled():
    """End-to-end through _expand_and_evaluate (not just the helper in
    isolation), confirming the two are actually wired together."""
    board = hanging_rook_board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    node = _MCTSNode(prior=1.0)

    engine = MCTSEngine(use_heuristic_priors=True)
    engine._expand_and_evaluate(board, Color.RED, node)

    n = len(legal_moves)
    priors = [child.prior for child in node.children.values()]
    assert not all(math.isclose(p, 1.0 / n) for p in priors)


def test_choose_move_still_works_end_to_end_with_heuristic_priors():
    """Not a correctness invariant the way SearchEngine's ordering
    features have (MCTS is inherently approximate -- different priors
    can and do change which move ends up with the most visits, unlike
    alpha-beta's exhaustive exploration), just confirms the full
    choose_move path doesn't crash and still returns a legal move."""
    board = hanging_rook_board()
    engine = MCTSEngine(simulations=50, use_heuristic_priors=True)

    result = engine.choose_move(board, Color.RED)

    legal_moves = Rule.generate_legal_moves(board, Color.RED)
    legal_pairs = {(m.from_pos, m.to_pos) for m in legal_moves}
    assert (result.best_move.from_pos, result.best_move.to_pos) in legal_pairs
