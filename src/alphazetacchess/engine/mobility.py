"""V0.4.3 mobility evaluation component.

This module deliberately stays separate from evaluation.py in the first
checkpoint.  We validate the signal and its symmetry before wiring it into
the leaf evaluation used by SearchEngine.

V0.4.3-beta-4 note: `mobility_score`/`mobility_balance` originally used
`Rule.generate_legal_moves` (fully legal moves -- excludes anything that
would leave the mover's own king in check). Beta-3's benchmark
(docs/v0.4.3_beta3-results.md) found this costs ~2.6x-3.2x wall-clock
time at the leaf, because full legality checking simulates every
candidate move to test for self-check -- the same expensive operation
that has been the established bottleneck since the V0.2 review.

Mobility only needs to be a cheap, approximate positional signal (how
much "room to move" does each side have), not an exact legal-move
count, so beta-4 switches the production functions to pseudo-legal
counting via MoveGenerator directly (no check-simulation). The old
fully-legal version is kept as `_mobility_score_legal_reference` purely
for A/B benchmarking, not used by evaluate()/SearchEngine.
"""

from ..core.rule import Rule
from ..core.board import Board
from ..core.move_generator import MoveGenerator
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

_move_generator = MoveGenerator()


def mobility_score(board, color):
    """Return weighted PSEUDO-legal move mobility for *color*.

    Uses MoveGenerator directly (piece movement patterns and blocking
    only -- no self-check / flying-general filtering), which is much
    cheaper than fully legal move generation and, for the purposes of
    a coarse positional signal, a perfectly reasonable approximation:
    mobility is meant to reward "having options", not to produce an
    exact legal-move count. See module docstring for the beta-3 → beta-4
    reasoning and measured cost.
    """
    score = 0
    for move in _move_generator.generate_moves(board, color):
        if move.moved_piece is not None:
            score += MOBILITY_WEIGHTS[move.moved_piece.type]
    return score


def mobility_balance(board, perspective_color):
    """Return own mobility minus opponent mobility (pseudo-legal, cheap)."""
    opponent = Board.opponent(perspective_color)
    return mobility_score(board, perspective_color) - mobility_score(
        board, opponent
    )


def _mobility_score_legal_reference(board, color):
    """
    The ORIGINAL (V0.4.3-beta-1 through beta-3) fully-legal
    implementation, kept only as a reference for A/B benchmarking
    against the pseudo-legal version above -- not used by
    evaluate()/SearchEngine. See docs/v0.4.3_beta4.md.
    """
    score = 0
    for move in Rule.generate_legal_moves(board, color):
        piece = board.get(*move.from_pos)
        if piece is not None:
            score += MOBILITY_WEIGHTS[piece.type]
    return score


def _mobility_balance_legal_reference(board, perspective_color):
    opponent = Board.opponent(perspective_color)
    return _mobility_score_legal_reference(
        board, perspective_color
    ) - _mobility_score_legal_reference(board, opponent)
