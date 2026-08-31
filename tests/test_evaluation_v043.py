"""V0.4.3-beta evaluation integration tests."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import evaluate


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


def test_mobility_disabled_preserves_v042_evaluation():
    board = Board()

    baseline = evaluate(
        board,
        Color.RED,
        use_piece_square_tables=True,
        use_king_safety=True,
    )
    explicit_off = evaluate(
        board,
        Color.RED,
        use_piece_square_tables=True,
        use_king_safety=True,
        use_mobility=False,
    )

    assert explicit_off == baseline


def test_mobility_term_is_zero_for_balanced_position():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    finalize(board)

    assert evaluate(
        board,
        Color.RED,
        use_piece_square_tables=False,
        use_king_safety=False,
        use_mobility=True,
    ) == 0


def test_mobility_changes_evaluation_when_one_side_has_more_moves():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.BLACK, 0, 5)
    finalize(board)

    without_mobility = evaluate(
        board,
        Color.RED,
        use_piece_square_tables=False,
        use_king_safety=False,
        use_mobility=False,
    )
    with_mobility = evaluate(
        board,
        Color.RED,
        use_piece_square_tables=False,
        use_king_safety=False,
        use_mobility=True,
        mobility_weight=1,
    )

    assert with_mobility - without_mobility != 0
