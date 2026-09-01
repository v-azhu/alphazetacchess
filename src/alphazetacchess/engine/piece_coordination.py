"""V0.4.5 piece coordination evaluation component.

Two classical, well-known Xiangqi coordination patterns, both about
Rooks and Cannons sharing a file:

- Doubled Rooks (双车): two friendly Rooks on the same file support
  each other and can combine their firepower along it.
- Rook-Cannon Battery (车炮连环): a friendly Rook and Cannon sharing a
  file form a powerful combined threat -- a Cannon needs a screen
  piece to capture, and any piece landing between them (including a
  future friendly piece, or simply repositioning) can turn this into
  one, while the Rook independently backs up the file regardless.

Deliberately NOT required: a clear line of sight between the two
pieces. "Same file" is treated as sufficient for this first version --
both pieces already exert independent pressure along that file, and
requiring an unobstructed path between them (a "real, immediately
usable" battery) is a natural refinement for later, not a correctness
requirement for a first, intentionally simple version. See
docs/v0.4.5.md.

Kept as its own small module and its own toggle
(use_piece_coordination), following the same pattern as
mobility.py/pawn_structure.py: independently benchmarkable,
independently disableable, and not assumed to help until measured.
"""

from ..core.board import Board
from ..core.piece import PieceType


DOUBLED_ROOKS_BONUS = 15
ROOK_CANNON_BATTERY_BONUS = 10

_COORDINATING_TYPES = (PieceType.ROOK, PieceType.CANNON)


def _rooks_and_cannons_by_file(board, color):
    """{file: [PieceType, ...]} for this color's Rooks/Cannons only."""
    files = {}
    for row in board.board:
        for piece in row:
            if piece is None or piece.color != color:
                continue
            if piece.type not in _COORDINATING_TYPES:
                continue
            files.setdefault(piece.x, []).append(piece.type)
    return files


def piece_coordination_score(board, color):
    files = _rooks_and_cannons_by_file(board, color)

    score = 0
    for piece_types in files.values():
        rooks = piece_types.count(PieceType.ROOK)
        cannons = piece_types.count(PieceType.CANNON)

        if rooks >= 2:
            score += DOUBLED_ROOKS_BONUS
        if rooks >= 1 and cannons >= 1:
            score += ROOK_CANNON_BATTERY_BONUS

    return score


def piece_coordination_balance(board, perspective_color):
    """Return own piece-coordination score minus the opponent's."""
    opponent = Board.opponent(perspective_color)
    return piece_coordination_score(
        board, perspective_color
    ) - piece_coordination_score(board, opponent)
