"""V0.4.1 correctness gates for Piece-Square Tables (PST).

Focused on the evaluation function itself (not the search), since PST
is purely a leaf-scoring change. See docs/v0.4.1.md for the design
rationale behind each table.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import (
    CALIBRATED_MATERIAL_VALUES,
    MATERIAL_VALUES,
    _king_safety_score,
    _piece_score,
    _pst_component,
    evaluate,
)
from alphazetacchess.engine.endgame import endgame_balance
from alphazetacchess.engine.mobility import mobility_balance
from alphazetacchess.engine.pawn_structure import pawn_structure_balance
from alphazetacchess.engine.piece_coordination import piece_coordination_balance


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def reference_evaluate(board, perspective_color, **options):
    material_values = options.get("material_values") or MATERIAL_VALUES
    use_piece_square_tables = options.get("use_piece_square_tables", True)
    use_king_safety = options.get("use_king_safety", True)
    pst_weight = options.get("pst_weight", 1)
    king_safety_weight = options.get("king_safety_weight", 1)
    score = 0
    for row in board.board:
        for piece in row:
            if piece is None:
                continue
            piece_score = _piece_score(piece, material_values)
            piece_score += pst_weight * _pst_component(
                piece, use_piece_square_tables
            )
            score += piece_score if piece.color == perspective_color else -piece_score
    if use_king_safety:
        opponent = Board.opponent(perspective_color)
        score += king_safety_weight * (
            _king_safety_score(board, perspective_color)
            - _king_safety_score(board, opponent)
        )
    if options.get("use_mobility", False):
        score += options.get("mobility_weight", 1) * mobility_balance(
            board, perspective_color
        )
    if options.get("use_pawn_structure", False):
        score += pawn_structure_balance(board, perspective_color)
    if options.get("use_piece_coordination", False):
        score += piece_coordination_balance(board, perspective_color)
    if options.get("use_endgame_heuristics", False):
        score += endgame_balance(board, perspective_color)
    return score


def test_inlined_evaluation_matches_reference_across_options():
    board = empty_board()
    for piece_type, color, x, y in (
        (PieceType.KING, Color.RED, 4, 0),
        (PieceType.KING, Color.BLACK, 3, 9),
        (PieceType.ROOK, Color.RED, 0, 5),
        (PieceType.CANNON, Color.BLACK, 4, 8),
        (PieceType.HORSE, Color.RED, 2, 5),
        (PieceType.PAWN, Color.BLACK, 6, 3),
        (PieceType.ADVISOR, Color.RED, 3, 0),
        (PieceType.ELEPHANT, Color.BLACK, 2, 9),
    ):
        board._place(Piece(piece_type, color, x, y))

    configurations = (
        {},
        {"use_piece_square_tables": False},
        {"use_king_safety": False},
        {
            "pst_weight": 10,
            "king_safety_weight": 8,
            "material_values": CALIBRATED_MATERIAL_VALUES,
        },
        {
            "use_mobility": True,
            "use_pawn_structure": True,
            "use_piece_coordination": True,
            "use_endgame_heuristics": True,
        },
    )
    for color in (Color.RED, Color.BLACK):
        for options in configurations:
            assert evaluate(board, color, **options) == reference_evaluate(
                board, color, **options
            )


def test_pst_is_color_symmetric_on_initial_position():
    # By construction, PST tables are RED-oriented and mirrored for
    # Black, so a fully symmetric position (the game's own starting
    # layout) must score exactly zero for both sides.
    board = Board()
    assert evaluate(board, Color.RED) == 0
    assert evaluate(board, Color.RED) == -evaluate(board, Color.BLACK)


def test_pst_prefers_a_centralised_horse_over_a_cornered_one_with_equal_material():
    central = empty_board()
    central._place(Piece(PieceType.KING, Color.RED, 4, 0))
    central._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    central._place(Piece(PieceType.HORSE, Color.RED, 4, 4))  # centre

    cornered = empty_board()
    cornered._place(Piece(PieceType.KING, Color.RED, 4, 0))
    cornered._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    cornered._place(Piece(PieceType.HORSE, Color.RED, 0, 0))  # own back-rank corner

    # Same material (one Horse each side), only the square differs.
    assert evaluate(central, Color.RED) > evaluate(cornered, Color.RED)


def test_pst_prefers_a_central_pawn_over_an_edge_pawn_after_crossing_the_river():
    central = empty_board()
    central._place(Piece(PieceType.KING, Color.RED, 4, 0))
    central._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    central._place(Piece(PieceType.PAWN, Color.RED, 4, 6))  # crossed, central file

    edge = empty_board()
    edge._place(Piece(PieceType.KING, Color.RED, 4, 0))
    edge._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    edge._place(Piece(PieceType.PAWN, Color.RED, 0, 6))  # crossed, edge file

    assert evaluate(central, Color.RED) > evaluate(edge, Color.RED)


def test_pst_disabled_reproduces_v02_baseline_exactly():
    # use_piece_square_tables=False must give the exact same score as
    # the pre-V0.4.1 evaluation: material + crossed-river pawn bonus +
    # a flat centre-file bonus for Horse/Cannon/Rook only (no PST term
    # for Pawn, and no development-rank term for anything).
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 6))

    CENTER_FILE_BONUS = 5
    expected = (
        MATERIAL_VALUES[PieceType.HORSE]
        + (4 - abs(4 - 4)) * CENTER_FILE_BONUS  # horse at x=4: 0 columns from centre
        + MATERIAL_VALUES[PieceType.PAWN]
        + 30  # PAWN_CROSSED_RIVER_BONUS
        # no centre-file bonus for Pawn in the old formula
    )

    assert evaluate(board, Color.RED, use_piece_square_tables=False) == expected


def test_pst_toggle_changes_the_score_for_a_position_where_it_matters():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 0, 0))  # corner: PST penalises this

    with_pst = evaluate(board, Color.RED, use_piece_square_tables=True)
    without_pst = evaluate(board, Color.RED, use_piece_square_tables=False)

    assert with_pst != without_pst


def test_search_engine_use_piece_square_tables_toggle_reaches_evaluation():
    # Exercises the actual wiring in search.py (four evaluate() call
    # sites all pass use_piece_square_tables=self.use_piece_square_tables)
    # by calling the leaf/quiescence entry point directly, the same way
    # tests/test_search_v034.py's quiescence tests do. Going through the
    # full choose_move() here would let Red's own move choice "fix" the
    # position within the single ply being searched, which would test
    # the search's move selection rather than the wiring itself.
    from alphazetacchess.engine.search import SearchEngine

    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 0, 0))  # corner

    # material_values/pst_weight/king_safety_weight pinned to the pre-V0.6.5
    # hand-guessed baseline here -- this test is about whether
    # use_piece_square_tables reaches evaluate(), not about which
    # material/weight defaults SearchEngine currently ships with, so it's
    # decoupled from that (see docs/v0.6.5.md).
    with_pst = SearchEngine(use_piece_square_tables=True,
                             material_values=MATERIAL_VALUES, pst_weight=1, king_safety_weight=1)
    without_pst = SearchEngine(use_piece_square_tables=False,
                                material_values=MATERIAL_VALUES, pst_weight=1, king_safety_weight=1)

    score_with = with_pst._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )
    score_without = without_pst._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score_with == evaluate(board, Color.RED, use_piece_square_tables=True)
    assert score_without == evaluate(board, Color.RED, use_piece_square_tables=False)
    assert score_with != score_without
