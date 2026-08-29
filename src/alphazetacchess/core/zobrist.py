"""Deterministic Zobrist hashing for Xiangqi positions."""

import random

from .piece import Color, PieceType


_SEED = 0xA17A_C0DE
_rng = random.Random(_SEED)

# Generate keys at module scope. Python class-body comprehensions do not
# reliably capture class-local variables while the comprehension executes.
PIECE_KEYS = {
    (color, piece_type, x, y): _rng.getrandbits(64)
    for color in (Color.RED, Color.BLACK)
    for piece_type in PieceType
    for y in range(10)
    for x in range(9)
}

SIDE_KEY = _rng.getrandbits(64)


class Zobrist:
    """Deterministic Zobrist hash key provider."""

    PIECE_KEYS = PIECE_KEYS
    SIDE_KEY = SIDE_KEY

    @classmethod
    def piece_key(cls, piece):
        return cls.PIECE_KEYS[
            (piece.color, piece.type, piece.x, piece.y)
        ]

    @classmethod
    def board_hash(cls, board):
        value = 0

        for y in range(board.HEIGHT):
            for x in range(board.WIDTH):
                piece = board.get(x, y)
                if piece is not None:
                    value ^= cls.PIECE_KEYS[
                        (piece.color, piece.type, x, y)
                    ]

        if board.current_player == Color.BLACK:
            value ^= cls.SIDE_KEY

        return value
