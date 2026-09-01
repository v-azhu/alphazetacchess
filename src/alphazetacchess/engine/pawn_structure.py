"""V0.4.4 pawn structure evaluation component.

Xiangqi-specific concept: Connected Pawns (联兵). Two pawns on adjacent
files at the same rank can mutually support each other -- once a pawn
crosses the river it gains sideways movement, so a same-rank neighbor
on an adjacent file is a real potential defender/recapture resource.
An isolated pawn (no same-rank neighbor on an adjacent file) has
nothing nearby to rely on if attacked, and this is a well-known
practical weakness in Xiangqi endgames, especially for advanced pawns.

Kept as its own small module with its own toggle (use_pawn_structure),
following the same pattern as mobility.py and the other V0.4.x
evaluation components: independently benchmarkable, independently
disableable, and not assumed to help until measured. See
docs/v0.4.4.md.
"""

from ..core.board import Board
from ..core.piece import PieceType


CONNECTED_PAWN_BONUS = 6
# Extra bonus, on top of the base bonus above, for a connected pawn
# that has also crossed the river -- an advanced pawn with support
# nearby is a real asset; the same pawn without that support is just
# as advanced but much easier to pick off.
CONNECTED_PAWN_CROSSED_RIVER_BONUS = 10


def _has_adjacent_file_neighbor(board, piece):
    """
    True if `piece` (assumed to be a Pawn) has a friendly Pawn on an
    adjacent file (x-1 or x+1) at the same rank (y).
    """
    for dx in (-1, 1):
        nx = piece.x + dx
        if not Board.in_bounds(nx, piece.y):
            continue
        neighbor = board.get(nx, piece.y)
        if (
            neighbor is not None
            and neighbor.type == PieceType.PAWN
            and neighbor.color == piece.color
        ):
            return True
    return False


def pawn_structure_score(board, color):
    score = 0

    for row in board.board:
        for piece in row:
            if piece is None or piece.color != color or piece.type != PieceType.PAWN:
                continue

            if _has_adjacent_file_neighbor(board, piece):
                score += CONNECTED_PAWN_BONUS
                if Board.has_crossed_river(piece.y, piece.color):
                    score += CONNECTED_PAWN_CROSSED_RIVER_BONUS

    return score


def pawn_structure_balance(board, perspective_color):
    """Return own pawn-structure score minus the opponent's."""
    opponent = Board.opponent(perspective_color)
    return pawn_structure_score(board, perspective_color) - pawn_structure_score(
        board, opponent
    )
