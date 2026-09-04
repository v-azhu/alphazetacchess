from ..core.piece import PieceType, Color
from ..core.board import Board
from .mobility import mobility_balance
from .pawn_structure import pawn_structure_balance
from .piece_coordination import piece_coordination_balance
from .endgame import endgame_balance


MATERIAL_VALUES = {
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.PAWN: 100,
    PieceType.KING: 0,
}

PAWN_CROSSED_RIVER_BONUS = 30
CENTER_FILE_BONUS = 5

# V0.4.1 -- Piece-Square Tables.
_HORSE_COLUMN_BONUS = [0, 4, 8, 12, 14, 12, 8, 4, 0]
_HORSE_DEV_BONUS = [-6, 0, 0, 4, 4, 8, 8, 4, 4, 2]
_CANNON_COLUMN_BONUS = [0, 2, 4, 6, 8, 6, 4, 2, 0]
_CANNON_DEV_BONUS = [0, 2, 6, 4, 2, 2, 2, 0, 0, -2]
_ROOK_COLUMN_BONUS = [0, 1, 2, 3, 4, 3, 2, 1, 0]
_ROOK_DEV_BONUS = [0, 0, 1, 1, 2, 2, 3, 4, 6, 8]
_PAWN_COLUMN_BONUS_BEFORE_RIVER = [0, 1, 2, 4, 5, 4, 2, 1, 0]
_PAWN_COLUMN_BONUS_AFTER_RIVER = [0, 4, 8, 14, 18, 14, 8, 4, 0]


def _build_dev_indexed_table(column_bonus, dev_bonus):
    table = [[0] * Board.WIDTH for _ in range(Board.HEIGHT)]
    for y in range(Board.HEIGHT):
        for x in range(Board.WIDTH):
            table[y][x] = column_bonus[x] + dev_bonus[y]
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
        score += PAWN_CROSSED_RIVER_BONUS
    if use_piece_square_tables:
        score += _pst_lookup(piece)
    elif piece.type in (PieceType.HORSE, PieceType.CANNON, PieceType.ROOK):
        score += _center_bonus(piece)
    return score


# V0.4.2 -- King Safety.
ADVISOR_ALIVE_BONUS = 20
ELEPHANT_ALIVE_BONUS = 12
OPEN_FILE_ROOK_PENALTY = -40
OPEN_FILE_CANNON_PENALTY = -25


def _guard_integrity_score(board, color):
    score = 0
    for row in board.board:
        for piece in row:
            if piece is None or piece.color != color:
                continue
            if piece.type == PieceType.ADVISOR:
                score += ADVISOR_ALIVE_BONUS
            elif piece.type == PieceType.ELEPHANT:
                score += ELEPHANT_ALIVE_BONUS
    return score


def _open_file_exposure_score(board, king):
    direction = 1 if king.color == Color.RED else -1
    y = king.y + direction
    while 0 <= y <= Board.HEIGHT - 1:
        piece = board.get(king.x, y)
        if piece is not None:
            if piece.color != king.color:
                if piece.type == PieceType.ROOK:
                    return OPEN_FILE_ROOK_PENALTY
                if piece.type == PieceType.CANNON:
                    return OPEN_FILE_CANNON_PENALTY
            return 0
        y += direction
    return 0


def _king_safety_score(board, color):
    king = board.find_king(color)
    if king is None:
        return 0
    return _guard_integrity_score(board, color) + _open_file_exposure_score(board, king)


def evaluate(
    board,
    perspective_color,
    use_piece_square_tables=True,
    use_king_safety=True,
    use_mobility=False,
    mobility_weight=1,
    use_pawn_structure=False,
    use_piece_coordination=False,
    use_endgame_heuristics=False,
):
    """Evaluate a position from perspective_color's point of view.

    V0.4.3 adds optional mobility as an independent evaluation term.
    It is disabled by default so the V0.4.2 evaluation remains the
    compatibility baseline. mobility_weight is exposed for A/B
    experiments and later tuning.

    V0.4.4 adds optional pawn structure (Connected Pawns) as another
    independent term, also disabled by default for the same reason.
    See docs/v0.4.4.md.

    V0.4.5 adds optional piece coordination (Doubled Rooks, Rook-Cannon
    Battery) as another independent term, also disabled by default.
    See docs/v0.4.5.md.

    V0.5.3 adds optional endgame-phase heuristics (Rook/Cannon value
    shift once major material has dropped low -- "车赛全局，炮怕残棋"),
    also disabled by default. See docs/v0.5.3.md.
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

    if use_king_safety:
        opponent_color = Board.opponent(perspective_color)
        score += _king_safety_score(board, perspective_color)
        score -= _king_safety_score(board, opponent_color)

    if use_mobility:
        score += mobility_weight * mobility_balance(board, perspective_color)

    if use_pawn_structure:
        score += pawn_structure_balance(board, perspective_color)

    if use_piece_coordination:
        score += piece_coordination_balance(board, perspective_color)

    if use_endgame_heuristics:
        score += endgame_balance(board, perspective_color)

    return score
