from ..core.piece import PieceType
from ..core.board import Board


# Approximate relative piece values (commonly cited values for
# Xiangqi -- e.g. a Rook is roughly worth a Cannon + a Horse). These
# are deliberately simple constants meant to be tuned later; this is
# the simplest possible "basic evaluation function" called for by
# V0.2 (see docs/roadmap.md). Mobility, king safety, and attack /
# defense terms are explicitly deferred to V0.4.
MATERIAL_VALUES = {
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
    # The King is never "captured" in this engine -- games end via
    # checkmate/stalemate detection in Rule/Search, so it carries no
    # material value here.
    PieceType.KING: 0,
}

# Small, easily-explainable positional bonuses (the "Position" term).
PAWN_CROSSED_RIVER_BONUS = 30
CENTER_FILE_BONUS = 5  # per column closer to the centre file (x=4)


def _center_bonus(piece):
    distance_from_center = abs(piece.x - 4)
    return (4 - distance_from_center) * CENTER_FILE_BONUS


def _piece_score(piece):
    score = MATERIAL_VALUES[piece.type]

    if piece.type == PieceType.PAWN and Board.has_crossed_river(piece.y, piece.color):
        # A pawn that has crossed the river can move sideways and
        # threatens more squares, so it is worth noticeably more.
        score += PAWN_CROSSED_RIVER_BONUS

    if piece.type in (PieceType.HORSE, PieceType.CANNON, PieceType.ROOK):
        # Cheap proxy for "mobility": pieces nearer the centre file
        # tend to control more squares. True mobility counting is
        # deferred to V0.4.
        score += _center_bonus(piece)

    return score


def evaluate(board, perspective_color):
    """
    Score the current position from `perspective_color`'s point of
    view: positive means `perspective_color` is better, negative
    means the opponent is better. Symmetric by construction:
    evaluate(board, RED) == -evaluate(board, BLACK).
    """
    score = 0

    for row in board.board:
        for piece in row:
            if piece is None:
                continue

            piece_score = _piece_score(piece)

            if piece.color == perspective_color:
                score += piece_score
            else:
                score -= piece_score

    return score
