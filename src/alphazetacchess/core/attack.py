from .board import Board
from .piece import Color, PieceType


class AttackDetector:
    """Specialized Xiangqi attack detector for position-level queries.

    This deliberately answers a narrower question than move generation:
    whether ``(x, y)`` is attacked by a given side in the current position.
    It does not construct Move objects and does not apply/undo moves.

    Flying-general is intentionally not handled here. It is a position-level
    rule and remains the responsibility of :class:`Rule`.
    """

    _ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
    _DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    _HORSE = (
        ((1, 2), (0, 1)),
        ((-1, 2), (0, 1)),
        ((1, -2), (0, -1)),
        ((-1, -2), (0, -1)),
        ((2, 1), (1, 0)),
        ((2, -1), (1, 0)),
        ((-2, 1), (-1, 0)),
        ((-2, -1), (-1, 0)),
    )

    @classmethod
    def is_attacked(cls, board, x, y, by_color):
        """Return whether square ``(x, y)`` is attacked by ``by_color``."""
        if not Board.in_bounds(x, y):
            return False

        if cls._orthogonal_attacked(board, x, y, by_color):
            return True
        if cls._horse_attacked(board, x, y, by_color):
            return True
        if cls._diagonal_attacked(board, x, y, by_color):
            return True
        if cls._king_attacked(board, x, y, by_color):
            return True
        if cls._pawn_attacked(board, x, y, by_color):
            return True
        return False

    @classmethod
    def _orthogonal_attacked(cls, board, x, y, by_color):
        """Check rook/cannon attacks along ranks and files."""
        for dx, dy in cls._ORTHOGONAL:
            cx, cy = x + dx, y + dy
            screen_found = False

            while Board.in_bounds(cx, cy):
                piece = board.get(cx, cy)
                if piece is None:
                    cx += dx
                    cy += dy
                    continue

                if not screen_found:
                    if piece.color == by_color and piece.type == PieceType.ROOK:
                        return True
                    # Any first piece can be the cannon's screen. A friendly
                    # piece for the attacking side still blocks a rook/cannon
                    # line and also serves as a screen for a later cannon.
                    screen_found = True
                    cx += dx
                    cy += dy
                    continue

                if piece.color == by_color and piece.type == PieceType.CANNON:
                    return True
                break

        return False

    @classmethod
    def _horse_attacked(cls, board, x, y, by_color):
        for (dx, dy), (leg_dx, leg_dy) in cls._HORSE:
            source_x = x - dx
            source_y = y - dy
            if not Board.in_bounds(source_x, source_y):
                continue

            leg_x = source_x + leg_dx
            leg_y = source_y + leg_dy
            if not Board.in_bounds(leg_x, leg_y):
                continue
            if board.get(leg_x, leg_y) is not None:
                continue

            piece = board.get(source_x, source_y)
            if piece is not None and piece.color == by_color and piece.type == PieceType.HORSE:
                return True
        return False

    @classmethod
    def _diagonal_attacked(cls, board, x, y, by_color):
        # Advisors move one diagonal square inside the palace.
        for dx, dy in cls._DIAGONAL:
            source_x = x - dx
            source_y = y - dy
            if not Board.in_bounds(source_x, source_y):
                continue
            piece = board.get(source_x, source_y)
            if (
                piece is not None
                and piece.color == by_color
                and piece.type == PieceType.ADVISOR
                and Board.in_palace(x, y, by_color)
            ):
                return True

        # Elephants move two diagonal squares and cannot cross the river.
        for dx, dy in cls._DIAGONAL:
            source_x = x - 2 * dx
            source_y = y - 2 * dy
            if not Board.in_bounds(source_x, source_y):
                continue
            piece = board.get(source_x, source_y)
            if piece is None or piece.color != by_color or piece.type != PieceType.ELEPHANT:
                continue
            eye_x = source_x + dx
            eye_y = source_y + dy
            if board.get(eye_x, eye_y) is not None:
                continue
            if Board.has_crossed_river(y, by_color):
                continue
            return True

        return False

    @classmethod
    def _king_attacked(cls, board, x, y, by_color):
        for dx, dy in cls._ORTHOGONAL:
            source_x = x - dx
            source_y = y - dy
            if not Board.in_bounds(source_x, source_y):
                continue
            piece = board.get(source_x, source_y)
            if piece is not None and piece.color == by_color and piece.type == PieceType.KING:
                return True
        return False

    @classmethod
    def _pawn_attacked(cls, board, x, y, by_color):
        # A pawn attacks forward. Once across the river it also attacks
        # horizontally, but it never attacks backward.
        forward = 1 if by_color == Color.RED else -1
        source_x = x
        source_y = y - forward
        if Board.in_bounds(source_x, source_y):
            piece = board.get(source_x, source_y)
            if piece is not None and piece.color == by_color and piece.type == PieceType.PAWN:
                return True

        for source_x in (x - 1, x + 1):
            source_y = y
            if not Board.in_bounds(source_x, source_y):
                continue
            piece = board.get(source_x, source_y)
            if piece is None or piece.color != by_color or piece.type != PieceType.PAWN:
                continue
            if Board.has_crossed_river(piece.y, by_color):
                return True

        return False
