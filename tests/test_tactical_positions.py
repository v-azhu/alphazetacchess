from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule


TACTICAL_POSITIONS = {
    "mate_in_one": {
        # Red is not in check. Red's horse can move 5,6 -> 3,7,
        # checking the Black king. The Red rook on file 3 covers
        # Black's 3,8 escape square, while the horse covers 5,8.
        "fen": "3aka3/4p4/9/5N5/9/9/9/9/9/3RK4 w - - 0 1",
        "side": Color.RED,
    },
    "free_capture": {
        "fen": "4k4/9/9/R3n4/9/9/9/9/9/4K4 w - - 0 1",
        "side": Color.RED,
    },
    "exchange_trap": {
        "fen": "4k4/9/9/4p4/9/9/9/r8/p8/R3K4 w - - 0 1",
        "side": Color.RED,
    },
}


def _move(board, from_pos, to_pos):
    return next(
        move
        for move in Rule.generate_legal_moves(board, board.current_player)
        if move.from_pos == from_pos and move.to_pos == to_pos
    )


def immediate_mates(board, color):
    """Return legal moves that leave the opponent checkmated."""
    mates = []
    for move in Rule.generate_legal_moves(board, color):
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            if Rule.is_checkmate(board, opponent):
                mates.append(move)
        finally:
            board.undo()
    return mates


def test_tactical_fixtures_are_legal_and_have_expected_objective_property():
    mate_board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    assert not Rule.is_in_check(mate_board, Color.RED)
    mates = immediate_mates(mate_board, Color.RED)
    assert mates

    free_board = board_from_fen(TACTICAL_POSITIONS["free_capture"]["fen"])
    capture = _move(free_board, (0, 6), (4, 6))
    assert capture.captured_piece is not None
    free_board.move(capture.from_pos, capture.to_pos)
    try:
        opponent_captures = [
            move
            for move in Rule.generate_legal_moves(free_board, Color.BLACK)
            if move.to_pos == capture.to_pos
        ]
        assert not opponent_captures
    finally:
        free_board.undo()

    trap_board = board_from_fen(TACTICAL_POSITIONS["exchange_trap"]["fen"])
    capture = _move(trap_board, (0, 0), (0, 1))
    assert capture.captured_piece is not None


def test_mate_in_one_fixture_has_no_hidden_mate_before_the_move():
    board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    assert Rule.is_checkmate(board, Color.BLACK) is False
    assert Rule.is_stalemate(board, Color.BLACK) is False


def test_tactical_helpers_restore_board_state():
    board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    before_hash = board.zobrist_hash
    before_player = board.current_player

    immediate_mates(board, Color.RED)

    assert board.zobrist_hash == before_hash
    assert board.current_player == before_player
