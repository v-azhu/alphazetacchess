"""V0.4.3 mobility component tests."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.mobility import mobility_balance, mobility_score


def empty_board():
    board = Board()
    board.board = [[None for _ in range(board.WIDTH)] for _ in range(board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def finalize(board):
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def test_mobility_is_symmetric_between_colors():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.PAWN, Color.RED, 4, 4)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.BLACK, 8, 9)
    finalize(board)

    assert mobility_balance(board, Color.RED) == -mobility_balance(
        board, Color.BLACK
    )


def test_rook_open_file_has_more_mobility_than_blocked_rook():
    open_board = empty_board()
    put(open_board, PieceType.KING, Color.RED, 4, 0)
    put(open_board, PieceType.KING, Color.BLACK, 4, 9)
    put(open_board, PieceType.PAWN, Color.RED, 4, 4)
    put(open_board, PieceType.ROOK, Color.RED, 0, 0)
    finalize(open_board)

    blocked_board = empty_board()
    put(blocked_board, PieceType.KING, Color.RED, 4, 0)
    put(blocked_board, PieceType.KING, Color.BLACK, 4, 9)
    put(blocked_board, PieceType.PAWN, Color.RED, 4, 4)
    put(blocked_board, PieceType.ROOK, Color.RED, 0, 0)
    put(blocked_board, PieceType.PAWN, Color.RED, 0, 1)
    finalize(blocked_board)

    assert mobility_score(open_board, Color.RED) > mobility_score(
        blocked_board, Color.RED
    )


def test_more_active_horse_increases_mobility():
    active = empty_board()
    put(active, PieceType.KING, Color.RED, 4, 0)
    put(active, PieceType.KING, Color.BLACK, 4, 9)
    put(active, PieceType.PAWN, Color.RED, 4, 4)
    put(active, PieceType.HORSE, Color.RED, 4, 2)
    finalize(active)

    blocked = empty_board()
    put(blocked, PieceType.KING, Color.RED, 4, 0)
    put(blocked, PieceType.KING, Color.BLACK, 4, 9)
    put(blocked, PieceType.PAWN, Color.RED, 4, 4)
    put(blocked, PieceType.HORSE, Color.RED, 1, 0)
    put(blocked, PieceType.PAWN, Color.RED, 2, 1)
    put(blocked, PieceType.PAWN, Color.RED, 0, 1)
    finalize(blocked)

    assert mobility_score(active, Color.RED) > mobility_score(
        blocked, Color.RED
    )
