from ..core.piece import PieceType, Color
from ..core.board import Board


# Approximate relative piece values (commonly cited values for
# Xiangqi -- e.g. a Rook is roughly worth a Cannon + a Horse). These
# are deliberately simple constants meant to be tuned later; this is
# the simplest possible "basic evaluation function" called for by
# V0.2 (see docs/roadmap.md).
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

PAWN_CROSSED_RIVER_BONUS = 30
CENTER_FILE_BONUS = 5  # per column closer to the centre file (x=4)


# ---------------------------------------------------------------------------
# V0.4.1 -- Piece-Square Tables (PST)
#
# These are hand-constructed from general, well-documented Xiangqi
# positional principles (noted per piece type below), NOT extracted
# from any specific published/tuned engine's table. They are a
# reasonable, explainable starting point; refining the exact numbers
# with real game data is deferred to V0.5 (self-play), consistent
# with the project's "measure before optimizing" principle.
#
# All tables are built from RED's point of view: row 0 is Red's own
# back rank, row 9 is Black's back rank. `_pst_lookup` mirrors the row
# (9 - y) for Black pieces so the same table can be reused for both
# colors (Xiangqi's board is left-right and (for this purpose)
# color-symmetric).
# ---------------------------------------------------------------------------

# --- Horse (马/馬): mobility lives and dies by having open squares to
# jump to, so corners and edges are bad and the centre is good. Early
# development toward the centre is good; charging alone deep into
# enemy territory without support is a well-known way to lose a horse
# ("blocked leg" / trapped-horse patterns), so the bonus tapers off
# (but stays positive) past the river rather than continuing to climb.
_HORSE_COLUMN_BONUS = [0, 4, 8, 12, 14, 12, 8, 4, 0]
_HORSE_DEV_BONUS = [-6, 0, 0, 4, 4, 8, 8, 4, 4, 2]

# --- Cannon (炮): needs a "screen" piece to capture, so its power is
# tied to the pieces around it more than to raw centrality -- the
# column bonus is therefore much flatter than the Horse's. The
# traditional strong opening square is the original cannon rank
# (development rank 2, e.g. "cannon to central file" openings keep it
# there); overextending alone past the river loses access to friendly
# screens, so the bonus turns slightly negative deep in enemy territory.
_CANNON_COLUMN_BONUS = [0, 2, 4, 6, 8, 6, 4, 2, 0]
_CANNON_DEV_BONUS = [0, 2, 6, 4, 2, 2, 2, 0, 0, -2]

# --- Rook (车): already powerful everywhere (unlimited range along
# open files/ranks), so its PST is intentionally the smallest-magnitude
# one here -- a small central-file preference, and a real bonus for
# reaching the opponent's back ranks ("infiltrating rook", 沉底车, a
# well-known strong pattern in Xiangqi endgame/middlegame play).
_ROOK_COLUMN_BONUS = [0, 1, 2, 3, 4, 3, 2, 1, 0]
_ROOK_DEV_BONUS = [0, 0, 1, 1, 2, 2, 3, 4, 6, 8]

# --- Pawn (兵/卒): before crossing the river a pawn's position barely
# matters (it can only push forward one square at a time); the
# existing PAWN_CROSSED_RIVER_BONUS already rewards crossing. What PST
# adds is the well-known distinction between central and edge pawns
# once across: central pawns support an attack on the palace, while
# edge pawns ("边兵/边卒") are traditionally considered the weakest
# pawns because, once past the river, they can only ever shuffle
# sideways then push straight into a corner of the board.
_PAWN_COLUMN_BONUS_BEFORE_RIVER = [0, 1, 2, 4, 5, 4, 2, 1, 0]
_PAWN_COLUMN_BONUS_AFTER_RIVER = [0, 4, 8, 14, 18, 14, 8, 4, 0]


def _build_dev_indexed_table(column_bonus, dev_bonus):
    table = [[0] * Board.WIDTH for _ in range(Board.HEIGHT)]
    for y in range(Board.HEIGHT):
        # Development rank as seen by a RED piece at this row (this
        # table is always read in RED's own frame; Black pieces are
        # looked up via the mirrored row, see _pst_lookup).
        dev = y
        for x in range(Board.WIDTH):
            table[y][x] = column_bonus[x] + dev_bonus[dev]
    return table


def _build_pawn_table():
    table = [[0] * Board.WIDTH for _ in range(Board.HEIGHT)]
    for y in range(Board.HEIGHT):
        crossed = Board.has_crossed_river(y, Color.RED)
        column_bonus = (
            _PAWN_COLUMN_BONUS_AFTER_RIVER
            if crossed
            else _PAWN_COLUMN_BONUS_BEFORE_RIVER
        )
        for x in range(Board.WIDTH):
            table[y][x] = column_bonus[x]
    return table


_PIECE_SQUARE_TABLES = {
    PieceType.HORSE: _build_dev_indexed_table(_HORSE_COLUMN_BONUS, _HORSE_DEV_BONUS),
    PieceType.CANNON: _build_dev_indexed_table(_CANNON_COLUMN_BONUS, _CANNON_DEV_BONUS),
    PieceType.ROOK: _build_dev_indexed_table(_ROOK_COLUMN_BONUS, _ROOK_DEV_BONUS),
    PieceType.PAWN: _build_pawn_table(),
    # King / Advisor / Elephant are left out of V0.4.1's scope on
    # purpose: their movement is so restricted (a handful of legal
    # squares total) that a full positional table adds little over
    # the flat value they already have, and king safety specifically
    # is called out as its own, separate V0.4 evaluation term (proximity
    # of defenders, open lines toward the king, etc.) rather than a
    # simple per-square lookup. See docs/v0.4.1.md.
}


def _pst_lookup(piece):
    table = _PIECE_SQUARE_TABLES.get(piece.type)
    if table is None:
        return 0

    row = piece.y if piece.color == Color.RED else Board.HEIGHT - 1 - piece.y
    return table[row][piece.x]


def _center_bonus(piece):
    distance_from_center = abs(piece.x - 4)
    return (4 - distance_from_center) * CENTER_FILE_BONUS


def _piece_score(piece, use_piece_square_tables):
    score = MATERIAL_VALUES[piece.type]

    if piece.type == PieceType.PAWN and Board.has_crossed_river(piece.y, piece.color):
        # A pawn that has crossed the river can move sideways and
        # threatens more squares, so it is worth noticeably more.
        score += PAWN_CROSSED_RIVER_BONUS

    if use_piece_square_tables:
        score += _pst_lookup(piece)
    elif piece.type in (PieceType.HORSE, PieceType.CANNON, PieceType.ROOK):
        # V0.2/V0.3 baseline positional term, kept reachable via
        # use_piece_square_tables=False so it stays available as the
        # A/B comparison baseline for V0.4.1 (see docs/v0.4.1.md).
        score += _center_bonus(piece)

    return score


def evaluate(board, perspective_color, use_piece_square_tables=True):
    """
    Score the current position from `perspective_color`'s point of
    view: positive means `perspective_color` is better, negative
    means the opponent is better. Symmetric by construction:
    evaluate(board, RED) == -evaluate(board, BLACK).

    `use_piece_square_tables` defaults to True (the V0.4.1 behavior).
    Passing False reproduces the V0.2/V0.3 evaluation exactly (material
    + crossed-river pawn bonus + a flat centre-file bonus for
    Horse/Cannon/Rook), which is kept as the regression/comparison
    baseline -- see docs/v0.4.1.md.
    """
    score = 0

    for row in board.board:
        for piece in row:
            if piece is None:
                continue

            piece_score = _piece_score(piece, use_piece_square_tables)

            if piece.color == perspective_color:
                score += piece_score
            else:
                score -= piece_score

    return score
