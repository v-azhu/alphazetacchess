from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen


def test_position_history_tracks_move_and_undo():
    board = Board()
    initial_hash = board.zobrist_hash

    board.move((1, 0), (0, 2))
    assert len(board.position_history) == 2
    assert board.position_history[-1] == board.zobrist_hash

    board.undo()
    assert len(board.position_history) == 1
    assert board.position_history == [initial_hash]
    assert board.zobrist_hash == initial_hash


def test_exact_position_repetition_counts_side_to_move():
    board = Board()

    cycle = [
        ((1, 0), (0, 2)),
        ((1, 9), (0, 7)),
        ((0, 2), (1, 0)),
        ((0, 7), (1, 9)),
    ]

    assert board.repetition_count() == 1
    assert not board.is_repetition()

    for from_pos, to_pos in cycle:
        board.move(from_pos, to_pos)

    assert board.repetition_count() == 2
    assert not board.is_repetition()

    for from_pos, to_pos in cycle:
        board.move(from_pos, to_pos)

    assert board.repetition_count() == 3
    assert board.is_repetition()


def test_fen_position_starts_new_repetition_history():
    fen = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    board = board_from_fen(fen)

    assert len(board.history) == 0
    assert len(board.position_history) == 1
    assert board.repetition_count() == 1


def test_repetition_minimum_validation():
    board = Board()

    try:
        board.is_repetition(minimum=0)
    except ValueError:
        pass
    else:
        raise AssertionError("minimum=0 must raise ValueError")
