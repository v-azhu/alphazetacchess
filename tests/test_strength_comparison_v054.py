"""V0.5.4 strength comparison tests (selfplay/strength_comparison.py)."""

import os
import tempfile

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.random_engine import RandomEngine
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.selfplay.strength_comparison import (
    estimate_elo_diff,
    run_comparison_match,
)


def _forced_mate_board():
    # Same forced-mate fixture pattern used throughout the V0.3.x-V0.5.x
    # test suite (see tests/test_selfplay_recorder_v051.py): Black's king
    # is fully boxed in by its own guards, Red's horse is one legal move
    # from delivering mate. A fresh Board() (and fresh pieces) is built on
    # every call -- callers that need the SAME starting position across
    # multiple games (e.g. a board_factory=) must call this repeatedly,
    # never share one mutated instance.
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.board[9][4] = Piece(PieceType.KING, Color.BLACK, 4, 9)
    board.board[9][3] = Piece(PieceType.ADVISOR, Color.BLACK, 3, 9)
    board.board[9][5] = Piece(PieceType.ADVISOR, Color.BLACK, 5, 9)
    board.board[8][4] = Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8)
    board.board[9][0] = Piece(PieceType.ROOK, Color.BLACK, 0, 9)  # avoids a
    #                                                              pre-existing stalemate
    board.board[5][6] = Piece(PieceType.HORSE, Color.RED, 6, 5)   # one move from mate
    board.board[0][3] = Piece(PieceType.KING, Color.RED, 3, 0)    # off Black's file
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


# ---------------------------------------------------------------------------
# estimate_elo_diff
# ---------------------------------------------------------------------------

def test_estimate_elo_diff_is_zero_at_fifty_percent():
    assert estimate_elo_diff(0.5) == 0.0


def test_estimate_elo_diff_is_positive_above_fifty_percent():
    assert estimate_elo_diff(0.75) > 0


def test_estimate_elo_diff_is_none_at_extremes():
    assert estimate_elo_diff(0.0) is None
    assert estimate_elo_diff(1.0) is None


# ---------------------------------------------------------------------------
# run_comparison_match
# ---------------------------------------------------------------------------

def test_zero_max_moves_gives_all_draws():
    # Every game hits play_recorded_game's max_moves=0 fast path
    # immediately -- fully deterministic, no real search needed.
    stats = run_comparison_match(
        engine_a_factory=RandomEngine,
        engine_b_factory=RandomEngine,
        games=4,
        max_moves=0,
    )

    assert stats["games"] == 4
    assert stats["a_wins"] == 0
    assert stats["b_wins"] == 0
    assert stats["draws"] == 4
    assert stats["a_score_rate"] == 0.5
    assert stats["elo_diff"] == 0.0


def test_colors_alternate_and_configs_are_stored_per_side():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "games.jsonl")

        run_comparison_match(
            engine_a_factory=RandomEngine,
            engine_b_factory=RandomEngine,
            games=3,
            max_moves=0,
            a_config={"who": "A"},
            b_config={"who": "B"},
            output_path=path,
        )

        records = load_records(path)

    assert len(records) == 3
    # game 0: A is Red (i even) -- game 1: B is Red -- game 2: A is Red again.
    assert records[0]["red_config"] == {"who": "A"}
    assert records[0]["black_config"] == {"who": "B"}
    assert records[1]["red_config"] == {"who": "B"}
    assert records[1]["black_config"] == {"who": "A"}
    assert records[2]["red_config"] == {"who": "A"}
    assert records[2]["black_config"] == {"who": "B"}


def test_a_win_is_credited_correctly_regardless_of_which_color_a_plays():
    # Both games start from the same forced-mate position (Red mates in
    # one, deterministically, at depth=2). Game 0 has A playing Red (A
    # should win); game 1 has B playing Red (B should win) -- this
    # specifically exercises the "credit the win to the right side, not
    # just to whoever played Red" logic, which a naive
    # winner-is-always-Red-or-always-A bug would get backwards on game 1.
    engine = SearchEngine(depth=2)

    stats = run_comparison_match(
        engine_a_factory=lambda: engine,
        engine_b_factory=lambda: engine,
        games=2,
        max_moves=5,
        board_factory=_forced_mate_board,
    )

    assert stats["a_wins"] == 1
    assert stats["b_wins"] == 1
    assert stats["draws"] == 0
    assert stats["a_score_rate"] == 0.5


def test_on_game_complete_callback_is_invoked_once_per_game():
    calls = []

    run_comparison_match(
        engine_a_factory=RandomEngine,
        engine_b_factory=RandomEngine,
        games=3,
        max_moves=0,
        on_game_complete=lambda i, record, a_is_red: calls.append((i, a_is_red)),
    )

    assert calls == [(0, True), (1, False), (2, True)]


def test_no_output_path_means_no_file_is_written():
    stats = run_comparison_match(
        engine_a_factory=RandomEngine,
        engine_b_factory=RandomEngine,
        games=2,
        max_moves=0,
        output_path=None,
    )

    assert stats["games"] == 2  # ran fine with no output_path at all
