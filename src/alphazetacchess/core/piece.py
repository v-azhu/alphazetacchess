from enum import Enum


class PieceType(Enum):
    KING = "K"
    ADVISOR = "A"
    ELEPHANT = "E"
    HORSE = "H"
    ROOK = "R"
    CANNON = "C"
    PAWN = "P"


class Color(Enum):
    RED = 1
    BLACK = -1


class Piece:
    def __init__(self, piece_type, color, x, y):
        self.type = piece_type
        self.color = color
        self.x = x
        self.y = y

    def position(self):
        return self.x, self.y

    def __repr__(self):
        prefix = "R" if self.color == Color.RED else "B"
        return prefix + self.type.value
