from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.piece import Piece, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.see import StaticExchangeEvaluator
from alphazetacchess.engine.search_see import SeeSearchEngine


def _capture(board, from_pos, to_pos):
    move = next(
        move
        for move in Rule.generate_legal_moves(board, board.current_player)
        if move.from_pos == from_pos and move.to_pos == to_pos
    )
    assert move.captured_piece is not None
    return move


def test_see_values_a_capture_with_no_recapture():
    board = board_from_fen("4k4/9/9/4p4/9/9/9/9/p8/R3K4 w - - 0 1")
    move = _capture(board, (0, 0), (0, 1))

    see = StaticExchangeEvaluator()

    assert see.evaluate_capture(board, move) == see.piece_value(move.captured_piece)


def test_see_accounts_for_forced_rook_recapture():
    board = board_from_fen("4k4/9/9/4p4/9/9/9/r8/p8/R3K4 w - - 0 1")
    move = _capture(board, (0, 0), (0, 1))

    see = StaticExchangeEvaluator()

    expected = see.piece_value(move.captured_piece) - see.piece_value(move.moved_piece)
    assert see.evaluate_capture(board, move) == expected


def test_see_does_not_modify_board():
    board = board_from_fen("4k4/9/9/4p4/9/9/9/r8/p8/R3K4 w - - 0 1")
    before = board.zobrist_hash
    move = _capture(board, (0, 0), (0, 1))

    StaticExchangeEvaluator().evaluate_capture(board, move)

    assert board.zobrist_hash == before
    assert board.current_player == Color.RED


def test_see_search_engine_uses_board_for_capture_ordering():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    for piece in (
        Piece(PieceType.KING, Color.RED, 4, 0),
        Piece(PieceType.KING, Color.BLACK, 5, 9),
        Piece(PieceType.ROOK, Color.RED, 0, 5),
        Piece(PieceType.ROOK, Color.RED, 8, 5),
        Piece(PieceType.PAWN, Color.BLACK, 0, 6),
        Piece(PieceType.HORSE, Color.BLACK, 8, 6),
    ):
        board._place(piece)
    captures = [
        move for move in Rule.generate_legal_moves(board, Color.RED)
        if move.captured_piece is not None
    ]
    engine = SeeSearchEngine(depth=3, use_see=True)

    engine._order_moves(captures, None, board=board)

    assert len(captures) == 2
    assert engine.see.calls == 2
