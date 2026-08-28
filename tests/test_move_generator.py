from alphazetacchess.core.board import Board
from alphazetacchess.core.move_generator import MoveGenerator
from alphazetacchess.core.piece import Color


def test_rook_initial_moves():
    board = Board()
    generator = MoveGenerator()

    moves = generator.generate_moves(
        board,
        Color.RED
    )

    rook_moves = {
        m.to_pos
        for m in moves
        if m.from_pos == (0, 0)
    }

    # 红车可以向前走两格，第三格被己方兵挡住。
    assert rook_moves == {
        (0, 1),
        (0, 2),
    }


def test_horse_initial_moves():
    board = Board()
    generator = MoveGenerator()

    moves = generator.generate_moves(
        board,
        Color.RED
    )

    horse_moves = {
        m.to_pos
        for m in moves
        if m.from_pos == (1, 0)
    }

    # 初始红马的两个马腿均为空。
    assert horse_moves == {
        (0, 2),
        (2, 2),
    }