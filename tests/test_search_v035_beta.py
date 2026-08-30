"""V0.3.5-beta tactical regression tests.

The positions are deliberately minimal, but they must still be legal Xiangqi
positions. In particular, the two generals may not face each other.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(board.WIDTH)] for _ in range(board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    return board


def put(board, piece_type, color, x, y):
    piece = Piece(piece_type, color, x, y)
    board.board[y][x] = piece
    return piece


def finalize(board):
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def sig(move):
    return None if move is None else (move.from_pos, move.to_pos)


def make_free_rook_position():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)

    # A blocker on the king file is mandatory; otherwise this is an
    # illegal "flying general" position.
    put(board, PieceType.PAWN, Color.RED, 4, 4)

    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.BLACK, 0, 5)
    return finalize(board)


def test_search_takes_free_high_value_piece():
    """A depth-1 search should prefer an immediately free rook."""
    board = make_free_rook_position()

    assert not Rule.is_in_check(board, Color.RED)
    assert not Rule.is_in_check(board, Color.BLACK)

    result = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=False,
    ).choose_move(board, Color.RED)

    assert sig(result.best_move) == ((0, 0), (0, 5))


def test_search_must_resolve_check():
    """When the side to move is in check, the returned move must evade it."""
    board = empty_board()

    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 8, 9)
    put(board, PieceType.ROOK, Color.BLACK, 4, 9)

    assert Rule.is_in_check(board, Color.RED)

    result = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=True,
    ).choose_move(board, Color.RED)

    assert result.best_move is not None
    assert Rule.is_legal_move(board, result.best_move, Color.RED)

    board.move(result.best_move.from_pos, result.best_move.to_pos)
    try:
        assert not Rule.is_in_check(board, Color.RED)
    finally:
        board.undo()


def test_quiescence_can_see_immediate_recapture():
    """QS must not treat a capture as a permanent gain when it is recaptured."""
    board = empty_board()

    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.PAWN, Color.RED, 4, 4)

    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.HORSE, Color.BLACK, 0, 5)
    put(board, PieceType.ROOK, Color.BLACK, 0, 9)
    finalize(board)

    without_qs = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=False,
    ).choose_move(board, Color.RED)

    with_qs = SearchEngine(
        depth=1,
        iterative_deepening=False,
        use_transposition_table=False,
        use_pvs=False,
        use_quiescence=True,
    ).choose_move(board, Color.RED)

    assert without_qs.best_move is not None
    assert with_qs.best_move is not None
    assert Rule.is_legal_move(board, with_qs.best_move, Color.RED)
    assert with_qs.score <= without_qs.score + 900
