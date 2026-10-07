from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.search_see import SeeSearchEngine


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


def test_killer_moves_keep_priority_over_history_in_base_and_see_search():
    take_pawn = capture((0, 0), (0, 1), PieceType.PAWN)
    killer = quiet((1, 0), (1, 1))
    history_favorite = quiet((2, 0), (2, 1))

    for engine_type in (SearchEngine, SeeSearchEngine):
        engine = engine_type(
            use_killer_moves=True,
            use_history=True,
            use_mvv_lva=True,
        )
        engine.killer_moves.record(4, killer)
        engine.history.reward(history_favorite, 8)

        ordered = engine._order_moves(
            [history_favorite, killer, take_pawn],
            None,
            ply=4,
        )

        assert ordered == [take_pawn, killer, history_favorite]


def test_history_ordering_reorders_quiets_without_reordering_captures():
    engine = SearchEngine(
        use_history=True,
        use_killer_moves=False,
        use_mvv_lva=False,
    )
    capture_a = capture((0, 0), (0, 1), PieceType.PAWN)
    quiet_a = quiet((1, 0), (1, 1))
    capture_b = capture((2, 0), (2, 1), PieceType.ROOK)
    quiet_b = quiet((3, 0), (3, 1))
    engine.history.reward(quiet_b, 8)

    ordered = engine._order_moves(
        [capture_a, quiet_a, capture_b, quiet_b],
        None,
    )

    assert ordered == [capture_a, quiet_b, capture_b, quiet_a]


def test_root_move_scores_order_prior_iteration_candidates_after_preferred_move():
    best = quiet((0, 0), (0, 1))
    next_best = quiet((1, 0), (1, 1))
    weakest = quiet((2, 0), (2, 1))
    scores = {
        (best.from_pos, best.to_pos): 5,
        (next_best.from_pos, next_best.to_pos): 4,
        (weakest.from_pos, weakest.to_pos): -2,
    }

    ordered = SearchEngine._order_root_moves(
        [weakest, next_best, best],
        best,
        scores,
    )

    assert ordered == [best, next_best, weakest]


def test_root_move_ordering_preserves_input_order_for_equal_scores():
    first = quiet((0, 0), (0, 1))
    second = quiet((1, 0), (1, 1))
    third = quiet((2, 0), (2, 1))
    scores = {
        (first.from_pos, first.to_pos): 3,
        (second.from_pos, second.to_pos): 3,
        (third.from_pos, third.to_pos): 3,
    }

    assert SearchEngine._order_root_moves(
        [first, second, third],
        None,
        scores,
    ) == [first, second, third]


def test_root_move_ordering_without_prior_scores_preserves_existing_behavior():
    first = quiet((0, 0), (0, 1))
    preferred = quiet((1, 0), (1, 1))
    last = quiet((2, 0), (2, 1))

    assert SearchEngine._order_root_moves(
        [first, preferred, last],
        preferred,
    ) == [preferred, first, last]
