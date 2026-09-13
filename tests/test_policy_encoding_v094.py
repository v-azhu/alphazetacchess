from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color
from alphazetacchess.neural.policy_encoding import (
    POLICY_DIM,
    NUM_SQUARES,
    move_to_policy_index,
    policy_index_to_squares,
)


def move(from_pos, to_pos):
    return Move(from_pos, to_pos)


def test_policy_dim_is_90_squares_squared():
    assert NUM_SQUARES == 90
    assert POLICY_DIM == 90 * 90


def test_round_trip_encode_decode_preserves_squares():
    m = move((2, 3), (5, 7))
    for color in (Color.RED, Color.BLACK):
        index = move_to_policy_index(m, color)
        from_pos, to_pos = policy_index_to_squares(index, color)
        assert from_pos == m.from_pos
        assert to_pos == m.to_pos


def test_index_is_within_policy_dim():
    m = move((0, 0), (8, 9))  # corner to corner, the extreme case
    for color in (Color.RED, Color.BLACK):
        index = move_to_policy_index(m, color)
        assert 0 <= index < POLICY_DIM


def test_mirrored_move_from_black_encodes_to_the_same_index_as_the_red_move():
    # Direct analogue of test_network_v062.py's own
    # test_perspective_relative_encoding_is_symmetric_under_color_and_flip:
    # a move and its vertical mirror should produce the IDENTICAL index
    # when each is encoded from its own side's perspective -- the whole
    # point of matching board_to_features's flip convention.
    red_move = move((2, 3), (5, 7))
    black_mirrored_move = move((2, 9 - 3), (5, 9 - 7))

    red_index = move_to_policy_index(red_move, Color.RED)
    black_index = move_to_policy_index(black_mirrored_move, Color.BLACK)

    assert red_index == black_index


def test_same_move_looks_different_from_each_sides_perspective():
    # Sanity check the flip actually does something: the SAME
    # unmirrored move, encoded as if chosen by each side, should
    # generally not produce the same index.
    m = move((2, 3), (5, 7))

    red_index = move_to_policy_index(m, Color.RED)
    black_index = move_to_policy_index(m, Color.BLACK)

    assert red_index != black_index


def test_different_moves_never_collide():
    moves = [
        move((0, 0), (0, 1)),
        move((0, 0), (1, 0)),
        move((1, 0), (0, 0)),
        move((8, 9), (8, 8)),
    ]
    for color in (Color.RED, Color.BLACK):
        indices = [move_to_policy_index(m, color) for m in moves]
        assert len(set(indices)) == len(moves)
