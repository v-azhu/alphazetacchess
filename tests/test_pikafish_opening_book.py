import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine
from tools.build_pikafish_opening_book import (
    BOOK_FORMAT,
    build_teacher_book,
    collect_frequent_positions,
)


class FakePikafishClient:
    def __init__(self, result):
        self.result = result
        self.positions = []

    def evaluate_fen(self, fen):
        self.positions.append(fen)
        return self.result


def test_collect_frequent_positions_counts_distinct_games_and_rejects_illegal_prefix():
    legal_opening = [((1, 2), (4, 2)), ((1, 9), (2, 7))]
    games = [
        (legal_opening, "DRAW"),
        (legal_opening, "RED_WINS"),
        ([((0, 1), (0, 2))], "BLACK_WINS"),
    ]

    parsed, rejected, visits, fens = collect_frequent_positions(games, max_ply=2)

    board = Board()
    first_key = f"{board.zobrist_hash}-RED"
    board.move((1, 2), (4, 2))
    second_key = f"{board.zobrist_hash}-BLACK"
    assert parsed == 3
    assert rejected == 1
    assert visits == {first_key: 2, second_key: 2}
    assert fens[first_key] == board_to_fen(Board())


def test_teacher_book_uses_pikafish_move_and_integrates_with_search():
    board = Board()
    key = f"{board.zobrist_hash}-RED"
    fen = board_to_fen(board)
    client = FakePikafishClient({
        "best_move": "b2e2",
        "score_cp": 24,
        "mate_in": None,
        "depth": 17,
    })

    book = build_teacher_book(
        {key: 500},
        {key: fen},
        client,
        min_visits=100,
        max_positions=None,
    )

    assert book["_format"] == BOOK_FORMAT
    assert book[key] == {
        "best_move": "b2e2",
        "score_cp": 24,
        "depth": 17,
        "source_games": 500,
        "fen": fen,
    }
    assert client.positions == [fen]

    result = SearchEngine(
        use_opening_book=True,
        opening_book=book,
    ).choose_move(board, Color.RED)
    assert result.from_book is True
    assert (result.best_move.from_pos, result.best_move.to_pos) == ((1, 2), (4, 2))


def test_teacher_book_rejects_illegal_engine_best_move():
    board = Board()
    key = f"{board.zobrist_hash}-RED"
    client = FakePikafishClient({
        "best_move": "a0a4",
        "score_cp": 0,
        "mate_in": None,
        "depth": 1,
    })

    with pytest.raises(RuntimeError, match="illegal move"):
        build_teacher_book(
            {key: 10},
            {key: board_to_fen(board)},
            client,
            min_visits=1,
            max_positions=None,
        )
