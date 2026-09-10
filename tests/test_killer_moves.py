from alphazetacchess.core.board import Board
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.killer_moves import KillerMoves
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def small_midgame_position():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 3))
    board._place(Piece(PieceType.HORSE, Color.RED, 2, 2))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 6))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 7, 7))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 5))
    return board


def test_killer_moves_keep_two_slots_and_promote_latest():
    table = KillerMoves()
    move1 = Move((0, 0), (0, 1))
    move2 = Move((1, 0), (1, 1))
    move3 = Move((2, 0), (2, 1))

    table.record(4, move1)
    table.record(4, move2)
    assert table.get(4) == (((1, 0), (1, 1)), ((0, 0), (0, 1)))

    table.record(4, move3)
    assert table.get(4) == (((2, 0), (2, 1)), ((1, 0), (1, 1)))

    table.record(4, move2)
    assert table.get(4) == (((1, 0), (1, 1)), ((2, 0), (2, 1)))


def test_killer_moves_ignore_captures():
    table = KillerMoves()
    capture = Move((0, 0), (0, 1))
    capture.captured_piece = Piece(PieceType.PAWN, Color.BLACK, 0, 1)

    table.record(2, capture)

    assert table.get(2) == ()


def test_killer_ordering_puts_quiet_killers_before_other_quiet_moves():
    # use_mvv_lva=False isolates killer-move ordering from V0.8.3's capture
    # ordering (also active inside _order_moves by default) -- see
    # tests/test_mvv_lva.py for the capture-ranking behavior itself and
    # tests/test_move_ordering.py for the two features combined.
    engine = SearchEngine(use_killer_moves=True, use_mvv_lva=False)
    killer = Move((2, 2), (2, 3))
    other = Move((1, 1), (1, 2))

    capture = Move((4, 4), (4, 5))
    capture.captured_piece = Piece(PieceType.PAWN, Color.BLACK, 4, 5)

    engine.killer_moves.record(3, killer)

    ordered = engine._order_moves([other, capture, killer], None, 3)

    assert ordered == [killer, other, capture]


def test_stale_capture_matching_a_killer_is_not_prioritized():
    # use_mvv_lva=False for the same reason as above: this test isolates
    # the killer table's own "captures are never promoted by a stale
    # coordinate match" rule from V0.8.3's independent capture-first
    # ordering, which would otherwise also move now_capture ahead of
    # other and make this test pass for the wrong reason.
    engine = SearchEngine(use_killer_moves=True, use_mvv_lva=False)
    killer = Move((2, 2), (2, 3))
    engine.killer_moves.record(3, killer)

    now_capture = Move((2, 2), (2, 3))
    now_capture.captured_piece = Piece(
        PieceType.PAWN, Color.BLACK, 2, 3
    )

    other = Move((1, 1), (1, 2))

    ordered = engine._order_moves([other, now_capture], None, 3)

    assert ordered == [other, now_capture]

def test_killer_moves_preserve_search_result():
    board = small_midgame_position()
    without = SearchEngine(depth=3, use_killer_moves=False)
    with_killers = SearchEngine(depth=3, use_killer_moves=True)

    result_without = without.choose_move(board, Color.RED)
    result_with = with_killers.choose_move(board, Color.RED)

    assert result_with.score == result_without.score
    assert result_with.best_move.from_pos == result_without.best_move.from_pos
    assert result_with.best_move.to_pos == result_without.best_move.to_pos
