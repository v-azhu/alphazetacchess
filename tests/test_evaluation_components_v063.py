"""V0.6.3 tests for engine/evaluation.py's evaluate_components() --
built to give tools/calibrate_evaluation.py raw regression features
for calibrating evaluate()'s hand-guessed constants against real
Pikafish scores. See evaluate_components()'s own docstring.

The central correctness gate: recombining these raw components with
the CURRENT hand-guessed constants must reproduce evaluate()'s own
output exactly. A decomposition that doesn't sum back to the same
total isn't a faithful decomposition of what evaluate() actually
computes, whatever else it reports.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import (
    evaluate,
    evaluate_components,
    MATERIAL_VALUES,
    PAWN_CROSSED_RIVER_BONUS,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def _recombine(components, include_optional_terms=False):
    """Reconstruct evaluate()'s score from raw components + current constants."""
    total = sum(
        components[f"material_{piece_type.name.lower()}"] * value
        for piece_type, value in MATERIAL_VALUES.items()
        if piece_type != PieceType.KING
    )
    total += components["pawn_crossed_river_diff"] * PAWN_CROSSED_RIVER_BONUS
    total += components["pst_balance"]
    total += components["king_safety_balance"]
    if include_optional_terms:
        total += components["mobility_balance"]
        total += components["pawn_structure_balance"]
        total += components["piece_coordination_balance"]
        total += components["endgame_balance"]
    return total


# ---------------------------------------------------------------------------
# The central correctness gate
# ---------------------------------------------------------------------------

def test_recombined_components_match_evaluate_on_starting_position():
    board = Board()

    for color in (Color.RED, Color.BLACK):
        components = evaluate_components(board, color)
        recombined = _recombine(components)
        direct = evaluate(board, color, use_piece_square_tables=True, use_king_safety=True)
        assert recombined == direct


def test_recombined_components_match_evaluate_on_an_asymmetric_position():
    board = Board()
    board.board[9][0] = None  # remove a Black Rook
    board.board[7][1] = None  # remove a Black Cannon

    for color in (Color.RED, Color.BLACK):
        components = evaluate_components(board, color)
        recombined = _recombine(components)
        direct = evaluate(board, color, use_piece_square_tables=True, use_king_safety=True)
        assert recombined == direct


def test_recombined_components_match_evaluate_with_every_optional_term_on():
    board = Board()
    board.board[9][0] = None
    board.board[7][1] = None

    components = evaluate_components(board, Color.RED)
    recombined = _recombine(components, include_optional_terms=True)
    direct = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True,
        use_mobility=True, use_pawn_structure=True,
        use_piece_coordination=True, use_endgame_heuristics=True,
    )
    assert recombined == direct


# ---------------------------------------------------------------------------
# Individual component sanity checks
# ---------------------------------------------------------------------------

def test_material_components_reflect_real_piece_counts():
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.RED, 8, 0)
    put(board, PieceType.ROOK, Color.BLACK, 0, 9)

    components = evaluate_components(board, Color.RED)

    assert components["material_rook"] == 1  # 2 own - 1 opponent
    assert components["material_cannon"] == 0
    assert components["material_pawn"] == 0


def test_material_components_have_no_king_entry():
    board = Board()
    components = evaluate_components(board, Color.RED)

    assert "material_king" not in components


def test_pawn_crossed_river_diff_counts_only_crossed_pawns():
    board = empty_board()
    # A Red pawn that has crossed the river (into Black's half) vs one that hasn't.
    put(board, PieceType.PAWN, Color.RED, 0, 6)  # crossed (Red crosses at y>=5)
    put(board, PieceType.PAWN, Color.RED, 1, 3)  # not crossed

    components = evaluate_components(board, Color.RED)

    assert components["pawn_crossed_river_diff"] == 1


def test_components_are_antisymmetric_between_colors():
    board = Board()
    board.board[9][0] = None

    red_components = evaluate_components(board, Color.RED)
    black_components = evaluate_components(board, Color.BLACK)

    for key in red_components:
        assert red_components[key] == -black_components[key]
