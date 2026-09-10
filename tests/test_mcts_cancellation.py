from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.mcts import MCTSEngine


class AlwaysStop:
    """Deterministic test double: cancelled before the first simulation
    can even run."""

    def is_set(self):
        return True


class StopAfterNSimulations:
    """Deterministic test double: lets exactly `n` simulations complete
    (is_set() is checked once per simulation, before it runs), then
    reports cancelled."""

    def __init__(self, n):
        self.n = n
        self.calls = 0

    def is_set(self):
        self.calls += 1
        return self.calls > self.n


def test_cancelled_before_first_simulation_falls_back_to_first_legal_move():
    board = Board()

    engine = MCTSEngine(simulations=200)
    result = engine.choose_move(board, Color.RED, stop_event=AlwaysStop())

    assert result.best_move is not None
    assert result.depth == 0  # completed_simulations, repurposing SearchResult.depth


def test_cancelled_after_some_simulations_uses_the_partial_tree():
    board = Board()

    engine = MCTSEngine(simulations=200)
    result = engine.choose_move(board, Color.RED, stop_event=StopAfterNSimulations(5))

    assert result.best_move is not None
    assert result.depth == 5


def test_cancellation_restores_board_state():
    board = Board()
    original_fen = board_to_fen(board)
    original_hash = board.zobrist_hash
    original_history = list(board.position_history)

    engine = MCTSEngine(simulations=200)
    engine.choose_move(board, Color.RED, stop_event=StopAfterNSimulations(5))

    assert board_to_fen(board) == original_fen
    assert board.zobrist_hash == original_hash
    assert board.position_history == original_history


def test_no_stop_event_runs_the_full_simulation_budget():
    board = Board()

    engine = MCTSEngine(simulations=30)
    result = engine.choose_move(board, Color.RED)

    assert result.depth == 30


def test_request_stop_before_a_call_does_not_cancel_that_call():
    """request_stop()/clear_stop() target self._stop_event, but
    choose_move(stop_event=None) clears that flag itself before using
    it (same convention as SearchEngine) -- so a pending request_stop()
    only matters for a search already in progress and sharing that
    same Event object (e.g. a caller that grabbed engine._stop_event
    directly), not for pre-emptively cancelling a future call."""
    board = Board()
    engine = MCTSEngine(simulations=30)

    engine.request_stop()
    result = engine.choose_move(board, Color.RED)

    assert result.depth == 30
