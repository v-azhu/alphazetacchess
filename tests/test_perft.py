import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.tools.perft import perft


# Standard Xiangqi initial-position legal-move counts.
INITIAL_PERFT = {
    1: 44,
    2: 1920,
    3: 79666,
    4: 3290240,
}


def test_perft_depth_zero():
    board = Board()
    assert perft(board, 0) == 1


def test_initial_position_depth_one():
    board = Board()
    assert perft(board, 1) == INITIAL_PERFT[1]


def test_initial_position_depth_two():
    board = Board()
    assert perft(board, 2) == INITIAL_PERFT[2]


def test_perft_rejects_negative_depth():
    with pytest.raises(ValueError):
        perft(Board(), -1)


def test_perft_restores_board_state():
    board = Board()
    before = str(board)
    before_hash = board.zobrist_hash
    before_player = board.current_player
    before_position_history = list(board.position_history)

    perft(board, 2)

    assert str(board) == before
    assert board.zobrist_hash == before_hash
    assert board.current_player == before_player
    assert board.history == []
    assert board.position_history == before_position_history
