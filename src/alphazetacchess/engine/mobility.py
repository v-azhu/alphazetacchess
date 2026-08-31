"""V0.4.3 mobility evaluation component.

This module deliberately stays separate from evaluation.py in the first
checkpoint.  We validate the signal and its symmetry before wiring it into
the leaf evaluation used by SearchEngine.
"""

from ..core.rule import Rule
from ..core.board import Board
from ..core.piece import Color, PieceType


# Mobility is a deliberately small positional signal.  Raw legal-move counts
# are useful, but giving every pawn/king move the same weight as a rook move
# would overvalue restricted pieces.  The first version therefore counts
# legal moves with piece-type weights.
MOBILITY_WEIGHTS = {
    PieceType.KING: 1,
    PieceType.ADVISOR: 1,
    PieceType.ELEPHANT: 1,
    PieceType.PAWN: 1,
    PieceType.HORSE: 2,
    PieceType.CANNON: 2,
    PieceType.ROOK: 2,
}


def mobility_score(board, color):
    """Return weighted legal-move mobility for *color*.

    The score is intentionally independent of material and piece-square
    tables.  It is also based on fully legal moves, so self-check and
    flying-general constraints are already respected.
    """
    score = 0
    for move in Rule.generate_legal_moves(board, color):
        piece = board.get(*move.from_pos)
        if piece is not None:
            score += MOBILITY_WEIGHTS[piece.type]
    return score


def mobility_balance(board, perspective_color):
    """Return own mobility minus opponent mobility."""
    opponent = Board.opponent(perspective_color)
    return mobility_score(board, perspective_color) - mobility_score(
        board, opponent
    )
