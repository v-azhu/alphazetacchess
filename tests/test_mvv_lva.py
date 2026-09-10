from alphazetacchess.core.board import Board
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.evaluation import CALIBRATED_MATERIAL_VALUES
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


def capture(from_pos, to_pos, attacker_type, victim_type):
    move = Move(from_pos, to_pos)
    move.moved_piece = Piece(attacker_type, Color.RED, *from_pos)
    move.captured_piece = Piece(victim_type, Color.BLACK, *to_pos)
    return move


def quiet(from_pos, to_pos, moved_type=PieceType.PAWN):
    move = Move(from_pos, to_pos)
    move.moved_piece = Piece(moved_type, Color.RED, *from_pos)
    return move


def test_captures_are_ordered_before_quiet_moves():
    engine = SearchEngine(use_mvv_lva=True, use_killer_moves=False)
    quiet_move = quiet((1, 1), (1, 2))
    capture_move = capture((0, 0), (0, 1), PieceType.HORSE, PieceType.PAWN)

    ordered = engine._order_moves([quiet_move, capture_move], None)

    assert ordered == [capture_move, quiet_move]


def test_higher_value_victim_ranks_before_lower_value_victim():
    engine = SearchEngine(use_mvv_lva=True, use_killer_moves=False)
    take_rook = capture((0, 0), (0, 1), PieceType.HORSE, PieceType.ROOK)
    take_pawn = capture((1, 0), (1, 1), PieceType.HORSE, PieceType.PAWN)

    ordered = engine._order_moves([take_pawn, take_rook], None)

    assert ordered == [take_rook, take_pawn]


def test_equal_victim_prefers_cheaper_attacker():
    engine = SearchEngine(use_mvv_lva=True, use_killer_moves=False)
    pawn_takes_rook = capture((0, 0), (0, 1), PieceType.PAWN, PieceType.ROOK)
    rook_takes_rook = capture((1, 0), (1, 1), PieceType.ROOK, PieceType.ROOK)

    ordered = engine._order_moves([rook_takes_rook, pawn_takes_rook], None)

    assert ordered == [pawn_takes_rook, rook_takes_rook]


def test_preferred_tt_move_still_ranks_first_over_captures():
    engine = SearchEngine(use_mvv_lva=True, use_killer_moves=False)
    preferred_quiet = quiet((1, 1), (1, 2))
    take_rook = capture((0, 0), (0, 1), PieceType.HORSE, PieceType.ROOK)

    preferred = (preferred_quiet.from_pos, preferred_quiet.to_pos)
    ordered = engine._order_moves([take_rook, preferred_quiet], preferred)

    assert ordered[0].from_pos == preferred_quiet.from_pos
    assert ordered[0].to_pos == preferred_quiet.to_pos


def test_material_values_override_is_used_for_scoring():
    default_engine = SearchEngine(use_mvv_lva=True)
    calibrated_engine = SearchEngine(use_mvv_lva=True, material_values=CALIBRATED_MATERIAL_VALUES)
    take_rook = capture((0, 0), (0, 1), PieceType.HORSE, PieceType.ROOK)

    default_score = default_engine._mvv_lva_score(take_rook)
    calibrated_score = calibrated_engine._mvv_lva_score(take_rook)

    # CALIBRATED_MATERIAL_VALUES rates a Rook well above the default table
    # (900 -> 1500, see engine/evaluation.py); the override must actually
    # change the score, not silently fall back to the module default.
    assert calibrated_score > default_score


def test_disabling_mvv_lva_preserves_prior_generator_order():
    engine = SearchEngine(use_mvv_lva=False, use_killer_moves=False)
    quiet_move = quiet((1, 1), (1, 2))
    capture_move = capture((0, 0), (0, 1), PieceType.HORSE, PieceType.ROOK)

    ordered = engine._order_moves([quiet_move, capture_move], None)

    assert ordered == [quiet_move, capture_move]


def test_mvv_lva_preserves_search_result():
    board = small_midgame_position()
    without = SearchEngine(depth=3, use_mvv_lva=False, use_killer_moves=False)
    with_mvv_lva = SearchEngine(depth=3, use_mvv_lva=True, use_killer_moves=False)

    result_without = without.choose_move(board, Color.RED)
    result_with = with_mvv_lva.choose_move(board, Color.RED)

    assert result_with.score == result_without.score
    assert result_with.best_move.from_pos == result_without.best_move.from_pos
    assert result_with.best_move.to_pos == result_without.best_move.to_pos
