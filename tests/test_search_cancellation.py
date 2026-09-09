from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchCancelled, SearchEngine


class StopOnFourthCheck:
    """Set the stop condition after the first root move is made."""

    def __init__(self):
        self.calls = 0

    def is_set(self):
        self.calls += 1
        return self.calls >= 4


class CancelAtDepthTwoEngine(SearchEngine):
    """Deterministic test double for the iterative-deepening boundary."""

    def _search_fixed_depth(self, board, color, legal_moves, depth, stop_event=None):
        if depth == 2:
            raise SearchCancelled
        return super()._search_fixed_depth(
            board, color, legal_moves, depth, stop_event
        )


def test_cancelled_search_restores_board_after_an_in_progress_move():
    board = Board()
    original_fen = board_to_fen(board)
    original_hash = board.zobrist_hash
    original_player = board.current_player
    original_history = list(board.position_history)

    engine = SearchEngine(depth=2, use_quiescence=False)
    stop_event = StopOnFourthCheck()

    result = engine.choose_move(board, Color.RED, stop_event=stop_event)

    assert result.best_move is not None
    assert result.depth == 0
    assert board_to_fen(board) == original_fen
    assert board.zobrist_hash == original_hash
    assert board.current_player == original_player
    assert board.position_history == original_history


def test_iterative_deepening_keeps_last_completed_depth_when_cancelled():
    board = Board()
    engine = CancelAtDepthTwoEngine(depth=3, use_quiescence=False)

    result = engine.choose_move(board, Color.RED)

    assert result.best_move is not None
    assert result.depth == 1
