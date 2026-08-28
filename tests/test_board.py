from alphazetacchess.core.board import Board


def test_initial_board():
    board = Board()

    assert board.get(4, 0) is not None
    assert board.get(4, 9) is not None


def test_move_and_undo():
    board = Board()

    board.move((0, 0), (0, 1))

    assert board.get(0, 1) is not None

    board.undo()

    assert board.get(0, 0) is not None
