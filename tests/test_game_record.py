import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.game_record import (
    GameRecord,
    RESULT_DRAW,
    RESULT_RED_WIN,
    TERMINATION_CHECKMATE,
    TERMINATION_REPETITION,
)


def test_move_to_iccs_uses_absolute_coordinates():
    board = Board()
    record = GameRecord.from_board(board)

    move = record.move_from_iccs("b0c2")
    assert record.move_to_iccs(move) == "b0c2"


def test_record_append_and_replay():
    board = Board()
    record = GameRecord.from_board(board)

    record.append_move(board, record.move_from_iccs("b0c2"))
    record.append_move(board, record.move_from_iccs("b9c7"))

    replayed = record.replay()
    assert board_to_fen(replayed) == board_to_fen(board)
    assert record.moves == ["b0c2", "b9c7"]
    assert record.result is None
    assert record.termination is None


def test_record_round_trip_dict():
    record = GameRecord.from_board(Board())
    record.moves = ["b0c2", "b9c7"]
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


def test_record_detects_threefold_exact_position_repetition():
    board = Board()
    record = GameRecord.from_board(board)

    cycle = ["b0c2", "b9c7", "c2b0", "c7b9"]
    for notation in cycle + cycle:
        record.append_move(board, record.move_from_iccs(notation))

    assert record.result == RESULT_DRAW
    assert record.termination == TERMINATION_REPETITION

    with pytest.raises(ValueError):
        record.append_move(board, record.move_from_iccs("b0c2"))


def test_record_detects_checkmate():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    from alphazetacchess.core.piece import Piece, PieceType, Color

    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.HORSE, Color.RED, 5, 7))
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board.current_player = Color.BLACK

    record = GameRecord.from_board(board)
    assert record.finalize() == (RESULT_RED_WIN, TERMINATION_CHECKMATE)
    assert record.result == RESULT_RED_WIN
    assert record.termination == TERMINATION_CHECKMATE
