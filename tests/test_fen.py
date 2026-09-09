from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.piece import Color, PieceType


START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


def test_start_position_fen_round_trip():
    board = board_from_fen(START_FEN)

    assert board_to_fen(board) == START_FEN
    assert board.current_player is Color.RED
    assert board.get(4, 0).type is PieceType.KING
    assert board.get(4, 9).type is PieceType.KING
    assert board.get(1, 2).type is PieceType.CANNON
    assert board.get(1, 7).type is PieceType.CANNON


def test_fen_uses_ucci_piece_letters_for_horse_and_elephant():
    fen = "4k4/9/9/9/9/9/9/9/2B1N4/4K4 w - - 0 1"
    board = board_from_fen(fen)

    assert board.get(2, 1).type is PieceType.ELEPHANT
    assert board.get(4, 1).type is PieceType.HORSE
    assert board.get(2, 1).color is Color.RED
    assert board.get(4, 1).color is Color.RED
    assert board_to_fen(board) == fen


def test_fen_import_initializes_position_history():
    board = board_from_fen(START_FEN)

    assert board.history == []
    assert board.position_history == [board.zobrist_hash]
    assert board.repetition_count() == 1


def test_fen_rejects_bad_rank_count():
    bad_fen = "9/9/9/9/9/9/9/9/9 w - - 0 1"

    try:
        board_from_fen(bad_fen)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for invalid rank count")


def test_fen_import_creates_normal_board_dimensions():
    board = board_from_fen(START_FEN)
    assert len(board.board) == Board.HEIGHT
    assert all(len(row) == Board.WIDTH for row in board.board)
