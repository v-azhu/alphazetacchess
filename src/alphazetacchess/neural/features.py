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

## Auxiliary hand-crafted features (added after the first real strength
## comparison showed the pure one-hot encoding losing to the heuristic
## `evaluate()` by -280 Elo -- see `docs/v0.6.2.md`'s 7th addendum)

The pure one-hot piece-position encoding gives the network no direct
signal for material balance, mobility, king safety, pawn structure, or
piece coordination -- it has to *discover* all of that from raw square
occupancy, which a small MLP evidently wasn't managing well from
~85k training examples (an earlier 4x-larger-network experiment barely
helped, pointing at the representation rather than capacity or data
volume as the bottleneck). Rather than asking the network to
rediscover heuristics `engine/evaluation.py` already computes and has
had five separate V0.4.x/V0.5.3 checkpoints refining, this appends
those exact same computed values as additional numeric features:
material balance, and the existing `mobility_balance`/
`pawn_structure_balance`/`piece_coordination_balance`/`endgame_balance`
functions, plus king safety (reusing `evaluate()`'s own private
`_king_safety_score` the same way `evaluate()` itself does) and both
sides' check status. The network's job changes from "learn these
heuristics from scratch" to "learn how to weigh, combine, and correct
these heuristics against Pikafish's actual judgment" -- a much easier,
more sample-efficient task, closer to a residual/boosting framing than
learning a value function from raw pixels.

All five `*_balance`-style functions are already perspective-relative
by construction (each takes `(board, color)` and returns "own minus
opponent" from that color's own viewpoint) -- calling them directly
with whichever `color` this module is encoding for is already
correctly oriented, no extra flip needed the way the one-hot planes
require. Each is divided by `AUX_FEATURE_SCALE` (500, the same
centipawn-ish normalization `engine/mcts.py`'s own `value_scale`
default uses) to keep these roughly comparable in magnitude to the
one-hot planes' `[0, 1]` values, rather than a raw material-balance
swing of, say, 900 dwarfing every other input's gradient contribution.

**Breaking change**: this changes `FEATURE_DIM`, so any network
trained on the old 1260-dim pure-one-hot encoding is NOT compatible
with this version and must be retrained (`tools/train_neural_eval.py`)
-- `SmallMLP.load()` will raise a shape-mismatch error at inference
time if fed the new, larger feature vectors, since the old file's
weight matrices were sized for the smaller input.
"""

import numpy as np

from ..core.board import Board
from ..core.piece import Color, PieceType
from ..core.rule import Rule
from ..engine.evaluation import MATERIAL_VALUES, _king_safety_score
from ..engine.mobility import mobility_balance
from ..engine.pawn_structure import pawn_structure_balance
from ..engine.piece_coordination import piece_coordination_balance
from ..engine.endgame import endgame_balance

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
_ONE_HOT_DIM = NUM_SQUARES * NUM_PIECE_TYPES * 2  # 1260

AUX_FEATURE_SCALE = 500
_AUX_NAMES = (
    "material_balance", "mobility_balance", "pawn_structure_balance",
    "piece_coordination_balance", "endgame_balance", "king_safety_balance",
    "own_in_check", "opponent_in_check",
)
NUM_AUX_FEATURES = len(_AUX_NAMES)  # 8

FEATURE_DIM = _ONE_HOT_DIM + NUM_AUX_FEATURES  # 1268


def _material_balance(board, color):
    opponent = Board.opponent(color)
    total = 0
    for row in board.board:
        for piece in row:
            if piece is None:
                continue
            value = MATERIAL_VALUES[piece.type]
            total += value if piece.color == color else -value
    return total


def _auxiliary_features(board, color):
    opponent = Board.opponent(color)
    king_safety_balance = _king_safety_score(board, color) - _king_safety_score(board, opponent)

    values = [
        _material_balance(board, color) / AUX_FEATURE_SCALE,
        mobility_balance(board, color) / AUX_FEATURE_SCALE,
        pawn_structure_balance(board, color) / AUX_FEATURE_SCALE,
        piece_coordination_balance(board, color) / AUX_FEATURE_SCALE,
        endgame_balance(board, color) / AUX_FEATURE_SCALE,
        king_safety_balance / AUX_FEATURE_SCALE,
        1.0 if Rule.is_in_check(board, color) else 0.0,
        1.0 if Rule.is_in_check(board, opponent) else 0.0,
    ]
    return np.array(values, dtype=np.float32)


def board_to_features(board, color):
    """
    Encode `board` as a `FEATURE_DIM`-length float32 vector, from
    `color`'s perspective: the first `_ONE_HOT_DIM` entries are the
    one-hot piece-position planes (see module docstring for the flip/
    relative-plane convention), followed by `NUM_AUX_FEATURES`
    hand-crafted balance-style features reusing `engine/evaluation.py`'s
    own sub-components.
    """
    one_hot = np.zeros(_ONE_HOT_DIM, dtype=np.float32)

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
            one_hot[plane * NUM_SQUARES + square_index] = 1.0

    aux = _auxiliary_features(board, color)
    return np.concatenate([one_hot, aux])
