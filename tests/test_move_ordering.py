from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.search import SearchEngine


def quiet(from_pos, to_pos):
    move = Move(from_pos, to_pos)
    move.moved_piece = Piece(PieceType.PAWN, Color.RED, *from_pos)
    return move


def capture(from_pos, to_pos, victim_type):
    move = Move(from_pos, to_pos)
    move.moved_piece = Piece(PieceType.HORSE, Color.RED, *from_pos)
    move.captured_piece = Piece(victim_type, Color.BLACK, *to_pos)
    return move


def test_full_priority_order_is_tt_move_then_captures_then_killers_then_other_quiets():
    """End-to-end ordering priority with every V0.8.x ordering layer on at
    once: TT/preferred move, MVV-LVA captures, killer quiet moves, other
    quiet moves -- the standard hash-move > captures > killers > quiets
    priority used by essentially every alpha-beta engine.
    """
    engine = SearchEngine(use_mvv_lva=True, use_killer_moves=True)

    preferred = quiet((0, 0), (0, 1))
    take_rook = capture((1, 0), (1, 1), PieceType.ROOK)
    take_pawn = capture((2, 0), (2, 1), PieceType.PAWN)
    killer = quiet((3, 0), (3, 1))
    other_quiet = quiet((4, 0), (4, 1))

    engine.killer_moves.record(5, killer)

    ordered = engine._order_moves(
        [other_quiet, killer, take_pawn, take_rook, preferred],
        (preferred.from_pos, preferred.to_pos),
        ply=5,
    )

    assert ordered == [preferred, take_rook, take_pawn, killer, other_quiet]
