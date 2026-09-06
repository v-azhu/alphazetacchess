"""V0.6.2 tests for neural/features.py and neural/network.py."""

import numpy as np
import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.neural.features import board_to_features, FEATURE_DIM
from alphazetacchess.neural.network import SmallMLP


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


# ---------------------------------------------------------------------------
# board_to_features
# ---------------------------------------------------------------------------

def test_feature_vector_has_expected_length_and_is_mostly_zero():
    board = Board()  # starting position, 32 pieces on the board

    features = board_to_features(board, Color.RED)

    assert features.shape == (FEATURE_DIM,)
    assert features.sum() == 32  # exactly one "1.0" per piece, rest zero


def test_perspective_relative_encoding_is_symmetric_under_color_and_flip():
    # A position and its vertical-flip-plus-color-swap mirror should
    # produce IDENTICAL feature vectors when each is encoded from its
    # own side's perspective -- this is the entire point of the
    # perspective-relative encoding (see features.py's module
    # docstring), and the easiest thing to get backwards (e.g.
    # flipping the board but forgetting to also swap "mine"/"theirs").
    original = empty_board()
    put(original, PieceType.ROOK, Color.RED, 2, 3)
    put(original, PieceType.HORSE, Color.BLACK, 5, 7)

    mirrored = empty_board()
    put(mirrored, PieceType.ROOK, Color.BLACK, 2, 9 - 3)
    put(mirrored, PieceType.HORSE, Color.RED, 5, 9 - 7)

    features_original = board_to_features(original, Color.RED)
    features_mirrored = board_to_features(mirrored, Color.BLACK)

    assert np.array_equal(features_original, features_mirrored)


def test_same_position_looks_different_from_each_sides_perspective():
    # Sanity check for the flip actually doing something: the SAME
    # unmirrored board, encoded from Red's vs Black's perspective,
    # should generally NOT produce the same vector (an asymmetric
    # position has no reason to look identical after an unmatched flip).
    board = empty_board()
    put(board, PieceType.ROOK, Color.RED, 2, 3)
    put(board, PieceType.HORSE, Color.BLACK, 5, 7)

    from_red = board_to_features(board, Color.RED)
    from_black = board_to_features(board, Color.BLACK)

    assert not np.array_equal(from_red, from_black)


# ---------------------------------------------------------------------------
# SmallMLP -- gradient correctness
# ---------------------------------------------------------------------------

def test_backward_matches_numerical_gradient():
    # The critical correctness check for any hand-derived backprop:
    # perturb a single weight slightly and confirm the measured change
    # in loss matches what the analytical gradient predicts. Far
    # stronger evidence than "training loss went down" alone -- the
    # same reasoning engine/mcts.py's dedicated sign-convention test
    # follows for its own hand-derived, easy-to-get-backwards math.
    rng = np.random.default_rng(0)
    net = SmallMLP(input_dim=6, hidden1=4, hidden2=3, seed=1)
    x = rng.standard_normal((5, 6))
    y_true = rng.standard_normal(5)

    y_pred, cache = net.forward(x)
    _, grads = net.backward(cache, y_pred, y_true)

    def loss_with_perturbed_w1(i, j, delta):
        original = net.w1[i, j]
        net.w1[i, j] = original + delta
        y_pred_perturbed, _ = net.forward(x)
        net.w1[i, j] = original
        return np.mean((y_pred_perturbed - y_true) ** 2)

    epsilon = 1e-4
    for i, j in [(0, 0), (2, 1), (5, 3)]:
        numerical_grad = (
            loss_with_perturbed_w1(i, j, epsilon) - loss_with_perturbed_w1(i, j, -epsilon)
        ) / (2 * epsilon)
        analytical_grad = grads["w1"][i, j]
        assert numerical_grad == pytest.approx(analytical_grad, abs=1e-3)


# ---------------------------------------------------------------------------
# SmallMLP -- can it actually learn anything?
# ---------------------------------------------------------------------------

def test_training_reduces_loss_on_a_tiny_synthetic_dataset():
    rng = np.random.default_rng(42)
    x = rng.standard_normal((20, 10)).astype(np.float32)
    true_weights = rng.standard_normal(10)
    y = x @ true_weights  # a simple linear target, well within a 2-hidden-layer MLP's capacity

    net = SmallMLP(input_dim=10, hidden1=16, hidden2=8, seed=2)

    initial_loss = net.train_step(x, y, lr=0.0)  # lr=0: measure, don't update
    for _ in range(300):
        final_loss = net.train_step(x, y, lr=0.01)

    assert final_loss < initial_loss * 0.5


def test_save_and_load_round_trip_produces_identical_predictions():
    import tempfile
    import os

    rng = np.random.default_rng(3)
    net = SmallMLP(input_dim=8, hidden1=6, hidden2=4, seed=4)
    x = rng.standard_normal((3, 8)).astype(np.float32)
    predictions_before = net.predict(x)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "net.npz")
        net.save(path)
        restored = SmallMLP.load(path)

    predictions_after = restored.predict(x)

    assert np.allclose(predictions_before, predictions_after)
