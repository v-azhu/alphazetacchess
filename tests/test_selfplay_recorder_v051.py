"""V0.5.1 self-play recording tests."""

import os
import tempfile

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.random_engine import RandomEngine
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.recorder import (
    play_recorded_game,
    append_record,
    load_records,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def test_zero_move_limit_gives_an_immediate_draw_record():
    # max_moves=0 means the while loop's condition is false before any
    # iteration, so the else clause fires immediately -- the fastest,
    # fully deterministic way to exercise the "hit the move limit"
    # path without waiting on a real game.
    record = play_recorded_game(RandomEngine(), RandomEngine(), max_moves=0)

    assert record["result"] == "DRAW"
    assert record["total_moves"] == 0
    assert record["moves"] == []


def test_record_has_the_expected_shape():
    record = play_recorded_game(
        RandomEngine(), RandomEngine(), max_moves=0,
        red_config={"depth": 2}, black_config={"depth": 1},
    )

    assert set(record.keys()) == {
        "red_config", "black_config", "result", "total_moves", "moves", "recorded_at",
    }
    assert record["red_config"] == {"depth": 2}
    assert record["black_config"] == {"depth": 1}
    assert isinstance(record["recorded_at"], float)


def test_a_decisive_forced_mate_game_records_the_correct_winner_and_moves():
    # Same forced-mate fixture pattern used throughout the V0.3.x/V0.4.x
    # test suite: Black's king is fully boxed in by its own advisors and
    # elephant, and Red's horse is one legal move from delivering mate.
    # Deterministic SearchEngine finds it immediately, giving a fast,
    # reliable decisive-game test instead of waiting on a real game.
    board = empty_board()
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ADVISOR, Color.BLACK, 3, 9)
    put(board, PieceType.ADVISOR, Color.BLACK, 5, 9)
    put(board, PieceType.ELEPHANT, Color.BLACK, 4, 8)
    put(board, PieceType.ROOK, Color.BLACK, 0, 9)  # unrelated mobility, avoids a
                                                    # pre-existing stalemate -- see
                                                    # tests/test_search_v033.py
    put(board, PieceType.HORSE, Color.RED, 6, 5)   # one move from mate
    put(board, PieceType.KING, Color.RED, 3, 0)    # off Black's file

    engine = SearchEngine(depth=2)
    record = play_recorded_game(engine, engine, max_moves=5, board=board)

    assert record["result"] == "RED_WINS"
    assert record["total_moves"] == 1
    assert record["moves"][0]["color"] == "RED"
    assert record["moves"][0]["from"] == [6, 5]
    assert record["moves"][0]["to"] == [5, 7]  # (6,5)->(5,7) delivers mate on (4,9)


def test_append_and_load_records_round_trip():
    record_a = play_recorded_game(RandomEngine(), RandomEngine(), max_moves=0)
    record_b = play_recorded_game(
        RandomEngine(), RandomEngine(), max_moves=0, red_config={"note": "second game"},
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "games.jsonl")

        append_record(path, record_a)
        append_record(path, record_b)

        loaded = load_records(path)

        assert len(loaded) == 2
        assert loaded[0]["result"] == record_a["result"]
        assert loaded[1]["red_config"] == {"note": "second game"}


def test_append_record_appends_rather_than_overwrites():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "games.jsonl")

        for _ in range(3):
            append_record(
                path, play_recorded_game(RandomEngine(), RandomEngine(), max_moves=0)
            )

        assert len(load_records(path)) == 3
