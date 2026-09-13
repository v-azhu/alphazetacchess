"""V0.9.4 move <-> policy-index encoding for a future trained policy
network's output layer.

Uses the exact same perspective-relative vertical-flip convention
`features.py`'s `board_to_features` already uses for its *input*
planes (see that module's own docstring): "my" home rank is always at
the same edge regardless of color, so a single canonical policy
network only ever has to learn one orientation of "a good move looks
like this" rather than two mirror-image versions -- same reasoning,
same flip rule, just applied to the network's OUTPUT space instead of
its input. `tests/test_policy_encoding_v094.py`'s
`test_mirrored_move_from_black_encodes_to_the_same_index_as_the_red_move`
is the direct analogue of `test_features_v062.py`'s own symmetry test.

Encoding: a move is (from-square, to-square), each a single square out
of `Board.WIDTH * Board.HEIGHT` (90) squares in *display* (perspective-
flipped) coordinates, giving `POLICY_DIM = 90 * 90 = 8100` possible
(from, to) pairs. This is a fixed, position-independent output space --
the large majority of indices are illegal for any given position (most
squares can't reach most other squares in one Xiangqi move at all), so
anything consuming these indices (training loss, MCTS prior
extraction) must mask down to the actually-legal moves for the current
position; this module only handles the index <-> move conversion, not
masking.
"""
from ..core.board import Board
from ..core.piece import Color

NUM_SQUARES = Board.WIDTH * Board.HEIGHT  # 90
POLICY_DIM = NUM_SQUARES * NUM_SQUARES  # 8100


def _display_square_index(x, y, color):
    display_y = y if color == Color.RED else (Board.HEIGHT - 1 - y)
    return display_y * Board.WIDTH + x


def _undo_display_square_index(square_index, color):
    display_y, x = divmod(square_index, Board.WIDTH)
    y = display_y if color == Color.RED else (Board.HEIGHT - 1 - display_y)
    return x, y


def move_to_policy_index(move, color):
    """`move`: anything with `.from_pos`/`.to_pos` (x, y) tuples, in
    real board coordinates -- `core.move.Move`'s own convention.
    `color`: whichever side is choosing this move (the perspective the
    resulting index is relative to), NOT necessarily `board.current_
    player` at any particular point -- matches `board_to_features`'s
    own `color` parameter meaning exactly.
    """
    from_index = _display_square_index(move.from_pos[0], move.from_pos[1], color)
    to_index = _display_square_index(move.to_pos[0], move.to_pos[1], color)
    return from_index * NUM_SQUARES + to_index


def policy_index_to_squares(index, color):
    """Inverse of `move_to_policy_index`: returns `(from_pos, to_pos)`
    as real-board-coordinate `(x, y)` tuples (not a `Move` object --
    reconstructing a real `Move` needs the actual piece being moved,
    which this module has no access to). Does not check whether the
    resulting move is legal, or even a geometrically valid move for any
    piece -- `POLICY_DIM` covers every (from-square, to-square) pair,
    the overwhelming majority of which no single Xiangqi move can ever
    make; callers (training/inference code) are responsible for only
    ever using indices that came from `move_to_policy_index` on an
    actually-legal move, or for masking network output down to the
    legal set before interpreting any index at all.
    """
    from_index, to_index = divmod(index, NUM_SQUARES)
    return (
        _undo_display_square_index(from_index, color),
        _undo_display_square_index(to_index, color),
    )
