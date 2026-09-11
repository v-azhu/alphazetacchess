"""V0.6.4 tests for engine/evaluation.py's pst_weight/king_safety_weight
parameters -- lets the V0.6.3 regression's PST/king-safety scaling
findings (docs/v0.6.3.md's Results section: ~9.9x and ~8.3x their
current implicit weight of 1) be tested, including alongside
material_values, rather than just material in isolation again (see
docs/v0.6.3.md's second addendum for the untested hypothesis this
exists to test, and docs/v0.6.4.md for this checkpoint's own writeup).

Follows the exact pattern tests/test_evaluation_components_v063.py's
own material_values tests already established: default preserves
behavior exactly, a weight change produces precisely the expected
delta (computed from evaluate_components()'s raw, unweighted value --
not re-derived by hand), and SearchEngine threads the override through
to _evaluate().
"""
from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.evaluation import (
    evaluate,
    evaluate_components,
    CALIBRATED_PST_WEIGHT,
    CALIBRATED_KING_SAFETY_WEIGHT,
)
from alphazetacchess.engine.search import SearchEngine


def asymmetric_board():
    # Deliberately built (not Board()'s default starting layout) to give
    # material_rook, pst_balance, AND king_safety_balance all nonzero --
    # an earlier version of this fixture (Board() minus one Black Rook)
    # gave 0 for pst_balance/king_safety_balance on this project's actual
    # tables, which made several of this file's delta assertions pass
    # vacuously (0 == 0) rather than by genuinely exercising the weight
    # scaling. The Horse/Rook are placed off the King's own file (x=4)
    # specifically so they don't block Black's Cannon's line to the King
    # (see _open_file_exposure_score) -- an earlier draft placed the
    # Horse on that file and silently zeroed king_safety_balance again.
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 2, 2))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 0, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 8, 5))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 8))  # open file to Red's King, not a check
    return board


def test_default_weights_preserve_existing_behavior():
    board = asymmetric_board()

    explicit_defaults = evaluate(board, Color.RED, pst_weight=1, king_safety_weight=1)
    implicit_defaults = evaluate(board, Color.RED)

    assert explicit_defaults == implicit_defaults


def test_pst_weight_scales_only_the_pst_contribution():
    board = asymmetric_board()
    components = evaluate_components(board, Color.RED)

    baseline = evaluate(board, Color.RED, pst_weight=1)
    weighted = evaluate(board, Color.RED, pst_weight=CALIBRATED_PST_WEIGHT)

    assert weighted - baseline == (CALIBRATED_PST_WEIGHT - 1) * components["pst_balance"]


def test_king_safety_weight_scales_only_the_king_safety_contribution():
    board = asymmetric_board()
    components = evaluate_components(board, Color.RED)

    baseline = evaluate(board, Color.RED, king_safety_weight=1)
    weighted = evaluate(board, Color.RED, king_safety_weight=CALIBRATED_KING_SAFETY_WEIGHT)

    assert weighted - baseline == (
        (CALIBRATED_KING_SAFETY_WEIGHT - 1) * components["king_safety_balance"]
    )


def test_weights_combine_independently_with_material_values():
    from alphazetacchess.engine.evaluation import CALIBRATED_MATERIAL_VALUES, MATERIAL_VALUES

    board = asymmetric_board()
    components = evaluate_components(board, Color.RED)

    baseline = evaluate(board, Color.RED)
    all_calibrated = evaluate(
        board, Color.RED,
        material_values=CALIBRATED_MATERIAL_VALUES,
        pst_weight=CALIBRATED_PST_WEIGHT,
        king_safety_weight=CALIBRATED_KING_SAFETY_WEIGHT,
    )

    # Sum over every piece type CALIBRATED_MATERIAL_VALUES actually
    # changes (Rook, Cannon, Horse -- see engine/evaluation.py), not
    # just Rook: this fixture's Cannon-count asymmetry (Black has one,
    # Red has none) means the Cannon term is nonzero too, and an
    # earlier version of this test only accounted for Rook, silently
    # passing by coincidence on a fixture where the Cannon/Horse terms
    # happened to cancel out.
    expected_material_delta = sum(
        components[f"material_{piece_type.name.lower()}"]
        * (CALIBRATED_MATERIAL_VALUES[piece_type] - MATERIAL_VALUES[piece_type])
        for piece_type in CALIBRATED_MATERIAL_VALUES
        if piece_type != PieceType.KING
    )
    expected_pst_delta = (CALIBRATED_PST_WEIGHT - 1) * components["pst_balance"]
    expected_king_safety_delta = (
        (CALIBRATED_KING_SAFETY_WEIGHT - 1) * components["king_safety_balance"]
    )

    assert all_calibrated - baseline == (
        expected_material_delta + expected_pst_delta + expected_king_safety_delta
    )


def test_search_engine_threads_weights_to_evaluate():
    # baseline_engine pins the pre-V0.6.5 hand-guessed weights explicitly --
    # SearchEngine() with no args now defaults to the CALIBRATED_* weights
    # itself (see docs/v0.6.5.md), so leaving this at bare SearchEngine()
    # would make both sides identical and the delta assertion vacuously
    # true (0 == 0) rather than actually testing the threading.
    board = asymmetric_board()

    baseline_engine = SearchEngine(pst_weight=1, king_safety_weight=1)
    calibrated_engine = SearchEngine(
        pst_weight=CALIBRATED_PST_WEIGHT,
        king_safety_weight=CALIBRATED_KING_SAFETY_WEIGHT,
    )

    baseline_score = baseline_engine._evaluate(board, Color.RED)
    calibrated_score = calibrated_engine._evaluate(board, Color.RED)

    components = evaluate_components(board, Color.RED)
    expected_delta = (
        (CALIBRATED_PST_WEIGHT - 1) * components["pst_balance"]
        + (CALIBRATED_KING_SAFETY_WEIGHT - 1) * components["king_safety_balance"]
    )
    assert calibrated_score - baseline_score == expected_delta


def test_recombined_components_match_evaluate_with_calibrated_weights():
    """The V0.6.3 correctness gate (evaluate_components()'s raw values,
    recombined with the constants actually in force, must reproduce
    evaluate()'s own output exactly) still holds for a non-default
    weighting, not just weight=1 -- confirming the components really
    are the *raw*, unweighted ingredients they claim to be."""
    board = asymmetric_board()
    components = evaluate_components(board, Color.RED)

    direct = evaluate(
        board, Color.RED,
        pst_weight=CALIBRATED_PST_WEIGHT,
        king_safety_weight=CALIBRATED_KING_SAFETY_WEIGHT,
    )

    from alphazetacchess.engine.evaluation import MATERIAL_VALUES, PAWN_CROSSED_RIVER_BONUS

    recombined = sum(
        components[f"material_{piece_type.name.lower()}"] * value
        for piece_type, value in MATERIAL_VALUES.items()
        if piece_type != PieceType.KING
    )
    recombined += components["pawn_crossed_river_diff"] * PAWN_CROSSED_RIVER_BONUS
    recombined += CALIBRATED_PST_WEIGHT * components["pst_balance"]
    recombined += CALIBRATED_KING_SAFETY_WEIGHT * components["king_safety_balance"]

    assert recombined == direct
