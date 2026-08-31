"""V0.4.2 correctness gates for King Safety (Guard Integrity + Open-File
Exposure). Focused on the evaluation function itself, following the same
pattern as tests/test_evaluation_v041.py. See docs/v0.4.2.md for the
design rationale behind each term.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import (
    evaluate,
    ADVISOR_ALIVE_BONUS,
    ELEPHANT_ALIVE_BONUS,
    OPEN_FILE_ROOK_PENALTY,
    OPEN_FILE_CANNON_PENALTY,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def test_king_safety_is_color_symmetric_on_initial_position():
    board = Board()
    assert evaluate(board, Color.RED) == 0
    assert evaluate(board, Color.RED) == -evaluate(board, Color.BLACK)


def test_advisor_worth_more_than_elephant_in_guard_integrity():
    # Documents the design intent directly: Advisors are confined to
    # (and so always guard) the palace itself, immediately next to the
    # king; Elephants are more general-purpose blockers and can never
    # enter the palace at all.
    assert ADVISOR_ALIVE_BONUS > ELEPHANT_ALIVE_BONUS


def test_open_file_rook_penalty_is_larger_than_cannon_penalty():
    # A Rook threatens the king's file directly and immediately; a
    # Cannon needs a screen to actually capture, so it is a real but
    # smaller threat.
    assert abs(OPEN_FILE_ROOK_PENALTY) > abs(OPEN_FILE_CANNON_PENALTY)


def test_guard_integrity_rewards_surviving_advisors_and_elephants():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 5, 0))
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 0))
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 6, 2))

    with_king_safety = evaluate(board, Color.RED, use_king_safety=True)
    without_king_safety = evaluate(board, Color.RED, use_king_safety=False)

    expected_delta = 2 * ADVISOR_ALIVE_BONUS + 2 * ELEPHANT_ALIVE_BONUS
    assert with_king_safety - without_king_safety == expected_delta


def test_open_file_exposure_penalizes_enemy_rook_on_open_file():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))  # different file: no flying-general risk
    board._place(Piece(PieceType.ROOK, Color.BLACK, 4, 8))  # clear shot down file 4

    with_king_safety = evaluate(board, Color.RED, use_king_safety=True)
    without_king_safety = evaluate(board, Color.RED, use_king_safety=False)

    assert with_king_safety - without_king_safety == OPEN_FILE_ROOK_PENALTY


def test_open_file_exposure_penalizes_enemy_cannon_on_open_file():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 8))

    with_king_safety = evaluate(board, Color.RED, use_king_safety=True)
    without_king_safety = evaluate(board, Color.RED, use_king_safety=False)

    assert with_king_safety - without_king_safety == OPEN_FILE_CANNON_PENALTY


def test_open_file_exposure_is_zero_when_file_is_blocked():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))  # blocks the file

    with_king_safety = evaluate(board, Color.RED, use_king_safety=True)
    without_king_safety = evaluate(board, Color.RED, use_king_safety=False)

    # No Advisor/Elephant placed either, so Guard Integrity is zero too
    # -- king safety should change nothing about this position's score.
    assert with_king_safety == without_king_safety


def test_king_safety_reflects_the_difference_between_both_sides():
    # Red has a full guard, Black has none at all. Red's own perspective
    # score must reflect the RELATIVE difference (its own guards minus
    # the opponent's), not just an absolute "does Red have guards" flag,
    # and symmetry must still hold from Black's perspective.
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 5, 0))

    red_perspective = evaluate(board, Color.RED, use_king_safety=True)
    black_perspective = evaluate(board, Color.BLACK, use_king_safety=True)

    assert red_perspective > 0
    assert red_perspective == -black_perspective


def test_pst_and_king_safety_toggles_are_independent():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 0, 0))   # PST-relevant (corner)
    board._place(Piece(PieceType.ROOK, Color.BLACK, 4, 8))  # king-safety-relevant

    both_off = evaluate(
        board, Color.RED, use_piece_square_tables=False, use_king_safety=False,
    )
    pst_only = evaluate(
        board, Color.RED, use_piece_square_tables=True, use_king_safety=False,
    )
    king_safety_only = evaluate(
        board, Color.RED, use_piece_square_tables=False, use_king_safety=True,
    )
    both_on = evaluate(
        board, Color.RED, use_piece_square_tables=True, use_king_safety=True,
    )

    pst_delta = pst_only - both_off
    king_safety_delta = king_safety_only - both_off

    # The two terms must not interact -- each contributes its own
    # independent delta, and turning both on sums them exactly.
    assert both_on - both_off == pst_delta + king_safety_delta


def test_search_engine_use_king_safety_toggle_reaches_evaluation():
    # Same approach as V0.4.1's wiring test: calls SearchEngine's
    # quiescence entry point directly (bypassing move search, which
    # would otherwise let Red's own move choice change the position
    # being scored) to prove the constructor flag actually reaches all
    # the way through to evaluation, not just that evaluate() itself
    # works in isolation.
    #
    # Deliberately uses a CANNON here rather than a ROOK: an enemy
    # Rook on a fully open file to the king is not just a positional
    # "Open-File Exposure" risk, it is an immediate check under
    # Rule.is_in_check (nothing blocks a Rook's line of sight). That
    # would make _quiescence take its "in check, must resolve, no
    # stand-pat" branch instead of the quiet stand-pat branch, which
    # legitimately returns a different value than a plain evaluate()
    # call -- correct quiescence behavior, but the wrong fixture for
    # testing evaluation wiring in isolation. A Cannon on the same
    # open file is a real King Safety threat (see
    # test_open_file_exposure_penalizes_enemy_cannon_on_open_file)
    # without being an immediate check, since a Cannon needs a screen
    # to actually capture -- so the position stays quiet here.
    from alphazetacchess.engine.search import SearchEngine

    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 8))  # open-file threat, not a check

    with_king_safety = SearchEngine(use_king_safety=True)
    without_king_safety = SearchEngine(use_king_safety=False)

    score_with = with_king_safety._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )
    score_without = without_king_safety._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score_with == evaluate(board, Color.RED, use_king_safety=True)
    assert score_without == evaluate(board, Color.RED, use_king_safety=False)
    assert score_with != score_without
