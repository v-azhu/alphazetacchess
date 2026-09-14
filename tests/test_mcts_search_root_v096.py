"""V0.9.6 tests for engine/mcts.py's search_root/root_visit_distribution --
the exposed raw root tree that choose_move itself is now built on top
of, used by tools/generate_mcts_policy_labels.py to record real
AlphaZero-style self-play policy targets (the search's own refined
opinion, not an external engine's independent one).
"""
import math

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.mcts import MCTSEngine


def test_search_root_returns_none_root_when_no_legal_moves():
    from alphazetacchess.core.board import Board as _Board
    board = _Board()
    board.board = [[None for _ in range(_Board.WIDTH)] for _ in range(_Board.HEIGHT)]

    engine = MCTSEngine(simulations=20)
    root, legal_moves, completed = engine.search_root(board, Color.RED)

    assert root is None
    assert legal_moves == []
    assert completed == 0


def test_search_root_matches_choose_move_on_the_same_call():
    """search_root is the exact same tree choose_move's own decision is
    based on -- the most-visited child there must be choose_move's
    best_move, using the same engine instance's own RNG-free
    determinism (MCTS here has no randomness -- PUCT selection is a
    deterministic argmax)."""
    board = Board()
    engine = MCTSEngine(simulations=60)

    root, legal_moves, completed = engine.search_root(board, Color.RED)
    best_move, best_child = max(root.children.items(), key=lambda item: item[1].visit_count)

    engine2 = MCTSEngine(simulations=60)
    result = engine2.choose_move(board, Color.RED)

    assert (best_move.from_pos, best_move.to_pos) == (
        result.best_move.from_pos, result.best_move.to_pos
    )
    assert completed == result.depth


def test_root_visit_distribution_sums_to_completed_simulations_minus_one():
    board = Board()
    engine = MCTSEngine(simulations=60)

    distribution = engine.root_visit_distribution(board, Color.RED)

    # The first simulation expands the root itself (no child selected
    # yet to visit); every simulation after that visits exactly one
    # root child on its way down. So total child visits = completed
    # simulations - 1, not completed simulations exactly.
    assert sum(distribution.values()) == 60 - 1


def test_root_visit_distribution_covers_every_legal_move():
    board = Board()
    engine = MCTSEngine(simulations=100)

    distribution = engine.root_visit_distribution(board, Color.RED)
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    assert len(distribution) == len(legal_moves)
    distribution_pairs = {(m.from_pos, m.to_pos) for m in distribution}
    legal_pairs = {(m.from_pos, m.to_pos) for m in legal_moves}
    assert distribution_pairs == legal_pairs


def test_root_visit_distribution_empty_when_cancelled_before_first_simulation():
    class AlwaysStop:
        def is_set(self):
            return True

    board = Board()
    engine = MCTSEngine(simulations=200)

    distribution = engine.root_visit_distribution(board, Color.RED, stop_event=AlwaysStop())

    assert distribution == {}


def test_root_visit_distribution_empty_when_no_legal_moves():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]

    engine = MCTSEngine(simulations=20)
    distribution = engine.root_visit_distribution(board, Color.RED)

    assert distribution == {}
