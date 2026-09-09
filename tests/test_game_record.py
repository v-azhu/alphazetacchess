import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.game_record import GameRecord


def test_move_to_iccs_uses_absolute_coordinates():
    board = Board()
    record = GameRecord.from_board(board)

    # Red right cannon: b0 -> e0.
    move = record.move_from_iccs("b0e0")
    assert record.move_to_iccs(move) == "b0e0"


def test_record_append_and_replay():
    board = Board()
    record = GameRecord.from_board(board)

    record.append_move(board, record.move_from_iccs("b0e0"))
    record.append_move(board, record.move_from_iccs("b9e9"))

    replayed = record.replay()
    assert board_to_fen(replayed) == board_to_fen(board)
    assert record.moves == ["b0e0", "b9e9"]


def test_record_round_trip_dict():
    record = GameRecord.from_board(Board())
    record.moves = ["b0e0", "b9e9"]
    # Validate the manually populated sequence through the public constructor.
    restored = GameRecord.from_dict(record.to_dict())

    assert restored.to_dict() == record.to_dict()
    assert restored.final_fen() == GameRecord.from_moves(
        record.initial_fen, record.moves
    ).final_fen()


def test_record_rejects_illegal_move():
    record = GameRecord.from_board(Board())

    with pytest.raises(ValueError):
        record.append_move(
            Board(),
            record.move_from_iccs("a0a9"),
        )


def test_record_rejects_bad_notation():
    with pytest.raises(ValueError):
        GameRecord.move_from_iccs("a0a")

    with pytest.raises(ValueError):
        GameRecord.move_from_iccs("j0a0")
