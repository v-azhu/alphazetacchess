"""V0.5.2 opening book tests."""

import os
import tempfile

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.selfplay.opening_book import (
    build_book_from_records,
    select_book_move,
    save_book,
    load_book,
)


def _record(color_sequence, moves, result):
    return {
        "red_config": {}, "black_config": {},
        "result": result, "total_moves": len(moves),
        "moves": [
            {"color": c, "from": f, "to": t} for c, (f, t) in zip(color_sequence, moves)
        ],
        "recorded_at": 0.0,
    }


# Two real opening replies for Red's first move (1,2)->(4,2) (cannon to
# centre): one line that goes on to win for Red, one that goes on to
# draw. Only the first ply matters for these tests -- max_ply=1 keeps
# them fast and focused.
WIN_RECORD = _record(
    ["RED", "BLACK"], [((1, 2), (4, 2)), ((1, 9), (2, 7))], "RED_WINS",
)
DRAW_RECORD = _record(
    ["RED", "BLACK"], [((7, 2), (4, 2)), ((1, 9), (2, 7))], "DRAW",
)


def test_build_book_counts_games_and_outcomes_per_move():
    book = build_book_from_records([WIN_RECORD, WIN_RECORD, DRAW_RECORD], max_ply=1)

    board = Board()
    key = f"{board.zobrist_hash}-RED"
    assert key in book

    win_move_stats = book[key]["1,2-4,2"]
    assert win_move_stats == {"wins": 2, "draws": 0, "losses": 0, "games": 2}

    draw_move_stats = book[key]["7,2-4,2"]
    assert draw_move_stats == {"wins": 0, "draws": 1, "losses": 0, "games": 1}


def test_build_book_respects_max_ply():
    book = build_book_from_records([WIN_RECORD], max_ply=1)

    board = Board()
    board.move((1, 2), (4, 2))
    key_after_first_move = f"{board.zobrist_hash}-BLACK"

    # Black's reply is the 2nd ply -- with max_ply=1, only the 1st ply
    # (Red's move) should have been recorded.
    assert key_after_first_move not in book


def test_select_book_move_prefers_higher_win_rate_above_min_games():
    book = build_book_from_records(
        [WIN_RECORD, WIN_RECORD, WIN_RECORD, DRAW_RECORD, DRAW_RECORD, DRAW_RECORD],
        max_ply=1,
    )

    board = Board()
    move = select_book_move(book, board, Color.RED, min_games=3)

    # Both candidate moves have 3 games each (>= min_games); the
    # all-wins line should be preferred over the all-draws line.
    assert move == ((1, 2), (4, 2))


def test_select_book_move_returns_none_below_min_games():
    book = build_book_from_records([WIN_RECORD], max_ply=1)  # only 1 game recorded

    board = Board()
    move = select_book_move(book, board, Color.RED, min_games=3)

    assert move is None


def test_select_book_move_returns_none_for_unknown_position():
    book = build_book_from_records([WIN_RECORD], max_ply=1)

    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)  # some position never recorded

    assert select_book_move(book, board, Color.RED, min_games=1) is None


def test_save_and_load_book_round_trip():
    book = build_book_from_records([WIN_RECORD, DRAW_RECORD], max_ply=1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "book.json")
        save_book(book, path)
        loaded = load_book(path)

        assert loaded == book


def test_search_engine_uses_book_move_when_confident():
    from alphazetacchess.engine.search import SearchEngine

    book = build_book_from_records([WIN_RECORD, WIN_RECORD, WIN_RECORD], max_ply=1)
    engine = SearchEngine(use_opening_book=True, opening_book=book, opening_book_min_games=3)

    board = Board()
    result = engine.choose_move(board, Color.RED)

    assert result.from_book is True
    assert result.best_move.from_pos == (1, 2)
    assert result.best_move.to_pos == (4, 2)
    assert result.nodes_evaluated == 0  # search never ran


def test_search_engine_falls_back_to_search_when_book_has_no_confident_entry():
    from alphazetacchess.engine.search import SearchEngine

    book = build_book_from_records([WIN_RECORD], max_ply=1)  # only 1 game, below default min_games
    engine = SearchEngine(depth=1, use_opening_book=True, opening_book=book, opening_book_min_games=3)

    board = Board()
    result = engine.choose_move(board, Color.RED)

    assert result.from_book is False
    assert result.best_move is not None


def test_search_engine_ignores_book_when_disabled():
    from alphazetacchess.engine.search import SearchEngine

    book = build_book_from_records([WIN_RECORD, WIN_RECORD, WIN_RECORD], max_ply=1)
    engine = SearchEngine(depth=1, use_opening_book=False, opening_book=book)

    board = Board()
    result = engine.choose_move(board, Color.RED)

    assert result.from_book is False
