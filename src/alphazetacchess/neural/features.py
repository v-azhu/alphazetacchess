"""V0.6.2 board -> feature-vector encoding, for the small MLP in
`neural/network.py` to consume.

## Perspective-relative, board-flipped encoding

Rather than encoding "Red pieces" / "Black pieces" directly (which
would force the network to separately learn two mirror-image versions
of every pattern -- "my general near the bottom" and "my general near
the top" -- since Red and Black start on opposite home ranks), this
encodes **"my pieces" vs "opponent pieces"**, and vertically flips the
board when encoding from Black's perspective so "my" side's home rank
is always at the same edge. This is standard practice for chess/
Xiangqi neural evaluators (NNUE-family networks do the same thing) and
means the network only ever has to learn one canonical orientation,
regardless of which color is actually being evaluated -- doubling the
effective sample efficiency of whatever training data exists, which
matters a lot for a small, laptop-trainable dataset (see
`docs/v0.6.2.md`).

`board_to_features(board, RED)` and `board_to_features(mirrored_board,
BLACK)` on a vertically-and-color-mirrored version of the same
position produce IDENTICAL feature vectors -- this symmetry is the
main thing `tests/test_features_v062.py` checks directly, since it's
easy to get the flip backwards (flip the board but forget to also
swap which pieces count as "mine") and only notice via a hard-to-debug
training result rather than a fast, direct unit test.
"""

import numpy as np

from ..core.board import Board
from ..core.piece import Color, PieceType

# Fixed, arbitrary-but-stable ordering of piece types within each
# 90-square "plane". Order doesn't matter for the network (it'll learn
# whatever weights fit), it only needs to be consistent between
# encoding calls and across save/load of a trained network.
_PIECE_TYPE_ORDER = (
    PieceType.ROOK,
    PieceType.HORSE,
    PieceType.ELEPHANT,
    PieceType.ADVISOR,
    PieceType.KING,
    PieceType.CANNON,
    PieceType.PAWN,
)
_PIECE_TYPE_INDEX = {piece_type: i for i, piece_type in enumerate(_PIECE_TYPE_ORDER)}

NUM_SQUARES = Board.WIDTH * Board.HEIGHT  # 90
NUM_PIECE_TYPES = len(_PIECE_TYPE_ORDER)  # 7
# 7 "my piece" planes + 7 "opponent piece" planes, each 90 squares.
FEATURE_DIM = NUM_SQUARES * NUM_PIECE_TYPES * 2  # 1260


def board_to_features(board, color):
    """
    Encode `board` as a `FEATURE_DIM`-length float32 vector, from
    `color`'s perspective (see module docstring for the flip/relative-
    plane convention). One-hot per occupied square: exactly one plane
    is set to 1.0 for each piece on the board, everything else 0.0.
    """
    features = np.zeros(FEATURE_DIM, dtype=np.float32)
    opponent = Board.opponent(color)

    for y in range(board.HEIGHT):
        # Flip vertically when encoding from Black's perspective, so
        # "my" home rank is always at display_y=0 regardless of color.
        display_y = y if color == Color.RED else (board.HEIGHT - 1 - y)
        for x in range(board.WIDTH):
            piece = board.board[y][x]
            if piece is None:
                continue

            square_index = display_y * board.WIDTH + x
            type_index = _PIECE_TYPE_INDEX[piece.type]
            # First 7 planes = my pieces, next 7 = opponent's.
            plane = type_index if piece.color == color else (type_index + NUM_PIECE_TYPES)
            features[plane * NUM_SQUARES + square_index] = 1.0

    return features
