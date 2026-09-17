from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.see import StaticExchangeEvaluator


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
    board = board_from_fen("4k4/9/9/4p4/9/9/r8/p8/R3K4 w - - 0 1")
    move = _capture(board, (0, 0), (0, 1))

    see = StaticExchangeEvaluator()

    expected = see.piece_value(move.captured_piece) - see.piece_value(move.moved_piece)
    assert see.evaluate_capture(board, move) == expected


def test_see_does_not_modify_board():
    board = board_from_fen("4k4/9/9/4p4/9/9/r8/p8/R3K4 w - - 0 1")
    before = board.zobrist_hash
    move = _capture(board, (0, 0), (0, 1))

    StaticExchangeEvaluator().evaluate_capture(board, move)

    assert board.zobrist_hash == before
    assert board.current_player == Color.RED
