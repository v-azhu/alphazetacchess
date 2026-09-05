"""V0.6.1 MCTS engine tests (engine/mcts.py).

Pays particular attention to the value-sign convention documented in
mcts.py's own module docstring -- getting a child's perspective backwards
is the single most common way to break a from-scratch MCTS/minimax
implementation, so it gets a dedicated, deliberately isolated unit test
(`test_select_child_prefers_the_move_good_for_the_parent`) rather than
relying only on end-to-end integration tests to catch it indirectly.
"""

import math

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.mcts import MCTSEngine, _MCTSNode, _squash
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def _forced_mate_board():
    # Same forced-mate fixture pattern used across the V0.3.x-V0.5.x
    # test suite: Black's king is fully boxed in by its own guards,
    # Red's horse is one legal move from delivering mate.
    board = empty_board()
    board.board[9][4] = Piece(PieceType.KING, Color.BLACK, 4, 9)
    board.board[9][3] = Piece(PieceType.ADVISOR, Color.BLACK, 3, 9)
    board.board[9][5] = Piece(PieceType.ADVISOR, Color.BLACK, 5, 9)
    board.board[8][4] = Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8)
    board.board[9][0] = Piece(PieceType.ROOK, Color.BLACK, 0, 9)
    board.board[5][6] = Piece(PieceType.HORSE, Color.RED, 6, 5)
    board.board[0][3] = Piece(PieceType.KING, Color.RED, 3, 0)
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


# ---------------------------------------------------------------------------
# _squash
# ---------------------------------------------------------------------------

def test_squash_zero_is_zero():
    assert _squash(0, value_scale=500) == 0.0


def test_squash_is_bounded_and_monotonic():
    low = _squash(-2000, value_scale=500)
    mid = _squash(100, value_scale=500)
    high = _squash(2000, value_scale=500)

    assert -1.0 < low < mid < high < 1.0


def test_squash_is_antisymmetric():
    assert _squash(300, value_scale=500) == -_squash(-300, value_scale=500)


# ---------------------------------------------------------------------------
# _MCTSNode
# ---------------------------------------------------------------------------

def test_node_starts_unexpanded():
    node = _MCTSNode(prior=1.0)

    assert node.expanded is False
    assert node.visit_count == 0
    assert node.is_terminal is False


def test_node_is_expanded_once_children_assigned():
    node = _MCTSNode(prior=1.0)
    node.children = {}

    assert node.expanded is True


# ---------------------------------------------------------------------------
# _select_child -- the critical sign-convention test
# ---------------------------------------------------------------------------

def test_select_child_prefers_the_move_good_for_the_parent():
    # Both children have been visited equally often (so the PUCT
    # exploration term U is identical for both, and Q alone decides).
    # Child "good_for_opponent" has accumulated a strongly POSITIVE
    # average value -- but that average is from the CHILD's own
    # to-move perspective, i.e. the OPPONENT's perspective relative to
    # the node choosing between them. A positive child average is
    # therefore actually BAD for the parent, and _select_child must
    # negate it to see that -- a naive (unnegated) implementation
    # would get this backwards and pick "good_for_opponent" instead.
    engine = MCTSEngine()
    node = _MCTSNode(prior=1.0)
    node.visit_count = 20

    good_for_opponent = _MCTSNode(prior=0.5)
    good_for_opponent.visit_count = 10
    good_for_opponent.value_sum = 8.0  # avg +0.8, from the OPPONENT's perspective

    good_for_parent = _MCTSNode(prior=0.5)
    good_for_parent.visit_count = 10
    good_for_parent.value_sum = -8.0  # avg -0.8, from the OPPONENT's perspective
    #                                    (i.e. GOOD for the parent, once negated)

    node.children = {
        "move_toward_opponent_advantage": good_for_opponent,
        "move_toward_parent_advantage": good_for_parent,
    }

    chosen_move, chosen_child = engine._select_child(node)

    assert chosen_move == "move_toward_parent_advantage"
    assert chosen_child is good_for_parent


def test_select_child_prefers_unvisited_child_when_all_else_equal():
    # With one child already visited (Q=0, neutral) and one never
    # visited (Q=0 by convention, but with a growing exploration bonus
    # as node.visit_count grows), PUCT should eventually favor giving
    # the unvisited child a look -- the entire point of the U term.
    engine = MCTSEngine(c_puct=1.4)
    node = _MCTSNode(prior=1.0)
    node.visit_count = 50  # many visits at the parent...

    visited_neutral = _MCTSNode(prior=0.5)
    visited_neutral.visit_count = 40
    visited_neutral.value_sum = 0.0  # exactly neutral average

    never_visited = _MCTSNode(prior=0.5)
    # visit_count stays 0

    node.children = {"visited": visited_neutral, "unvisited": never_visited}

    chosen_move, _ = engine._select_child(node)

    assert chosen_move == "unvisited"


# ---------------------------------------------------------------------------
# _expand_and_evaluate -- terminal detection
# ---------------------------------------------------------------------------

def test_expand_marks_checkmate_as_certain_loss():
    # Red horse + advisors box in Black's king with no legal replies
    # (mirrors the forced-mate fixture's post-mate position).
    board = _forced_mate_board()
    # Play the mating move directly to get to the actual mated position.
    engine_oracle = SearchEngine(depth=2)
    mating_move = engine_oracle.choose_move(board, Color.RED).best_move
    board.move(mating_move.from_pos, mating_move.to_pos)
    assert Rule.is_in_check(board, Color.BLACK)
    assert Rule.generate_legal_moves(board, Color.BLACK) == []

    engine = MCTSEngine()
    node = _MCTSNode(prior=1.0)
    value = engine._expand_and_evaluate(board, Color.BLACK, node)

    assert node.is_terminal is True
    assert node.terminal_value == -1.0
    assert value == -1.0


def test_expand_creates_uniform_priors_summing_to_one_for_normal_position():
    board = Board()  # starting position, definitely not terminal
    engine = MCTSEngine()
    node = _MCTSNode(prior=1.0)

    value = engine._expand_and_evaluate(board, Color.RED, node)

    assert node.is_terminal is False
    assert node.expanded is True
    assert -1.0 <= value <= 1.0
    total_prior = sum(child.prior for child in node.children.values())
    assert math.isclose(total_prior, 1.0)
    legal_move_count = len(Rule.generate_legal_moves(board, Color.RED))
    assert len(node.children) == legal_move_count


# ---------------------------------------------------------------------------
# choose_move -- integration
# ---------------------------------------------------------------------------

def test_choose_move_returns_a_legal_move_from_the_starting_position():
    board = Board()
    engine = MCTSEngine(simulations=60)

    result = engine.choose_move(board, Color.RED)

    legal_pairs = {
        (m.from_pos, m.to_pos) for m in Rule.generate_legal_moves(board, Color.RED)
    }
    assert (result.best_move.from_pos, result.best_move.to_pos) in legal_pairs
    assert result.nodes_evaluated > 0
    assert result.depth == 60  # simulations count, repurposing SearchResult.depth


def test_choose_move_returns_none_when_no_legal_moves():
    board = _forced_mate_board()
    engine_oracle = SearchEngine(depth=2)
    mating_move = engine_oracle.choose_move(board, Color.RED).best_move
    board.move(mating_move.from_pos, mating_move.to_pos)

    engine = MCTSEngine(simulations=10)
    result = engine.choose_move(board, Color.BLACK)

    assert result.best_move is None


def test_choose_move_finds_the_same_mate_in_one_as_search_engine():
    # Cross-validates MCTSEngine against the already-trusted
    # alpha-beta oracle on a forced-mate position, rather than hand-
    # verifying the exact winning square myself: whatever SearchEngine
    # (depth=2) finds as the mating move, MCTSEngine with enough
    # simulations should converge to the same move, since a certain,
    # saturated win (terminal_value=-1.0 for the opponent) dominates
    # every other line's bounded heuristic value.
    board = _forced_mate_board()

    oracle_move = SearchEngine(depth=2).choose_move(board, Color.RED).best_move

    mcts_move = MCTSEngine(simulations=300).choose_move(board, Color.RED).best_move

    assert (mcts_move.from_pos, mcts_move.to_pos) == (
        oracle_move.from_pos,
        oracle_move.to_pos,
    )
