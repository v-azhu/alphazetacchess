"""V0.6.2 tests for neural/features.py and neural/network.py."""

import numpy as np
import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.neural.features import board_to_features, FEATURE_DIM, AUX_FEATURE_SCALE, _AUX_NAMES
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
# board_to_features -- auxiliary hand-crafted features (added after the
# first real strength comparison showed the pure one-hot encoding
# losing to the heuristic evaluate() -- see docs/v0.6.2.md's 7th addendum)
# ---------------------------------------------------------------------------

def test_feature_dim_includes_the_auxiliary_features():
    assert FEATURE_DIM == 1268  # 1260 one-hot + 8 auxiliary


def test_auxiliary_features_are_zero_on_the_symmetric_starting_position():
    board = Board()
    features = board_to_features(board, Color.RED)

    aux = features[1260:]
    assert np.allclose(aux, 0.0)


def test_material_balance_feature_reflects_a_real_material_difference():
    board = Board()
    board.board[9][0] = None  # remove a Black rook -- Red is now up a Rook

    from_red = board_to_features(board, Color.RED)
    from_black = board_to_features(board, Color.BLACK)

    material_index = 1260 + _AUX_NAMES.index("material_balance")
    assert from_red[material_index] == pytest.approx(900 / AUX_FEATURE_SCALE)
    assert from_black[material_index] == pytest.approx(-900 / AUX_FEATURE_SCALE)


def test_auxiliary_features_are_symmetric_under_the_same_mirror_as_one_hot():
    # Same mirror-image construction as the one-hot symmetry test above
    # -- the auxiliary features must respect the same "my/theirs,
    # flipped for Black" convention, not just the one-hot planes.
    original = empty_board()
    put(original, PieceType.ROOK, Color.RED, 2, 3)
    put(original, PieceType.HORSE, Color.BLACK, 5, 7)

    mirrored = empty_board()
    put(mirrored, PieceType.ROOK, Color.BLACK, 2, 9 - 3)
    put(mirrored, PieceType.HORSE, Color.RED, 5, 9 - 7)

    features_original = board_to_features(original, Color.RED)
    features_mirrored = board_to_features(mirrored, Color.BLACK)

    assert np.array_equal(features_original[1260:], features_mirrored[1260:])


def test_own_and_opponent_in_check_features():
    # A position where Black's king has no escort and Red's Rook
    # delivers check along the open file -- own_in_check should be 1.0
    # from Black's perspective, 0.0 from Red's.
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 4, 5)

    own_check_index = 1260 + _AUX_NAMES.index("own_in_check")
    opponent_check_index = 1260 + _AUX_NAMES.index("opponent_in_check")

    from_black = board_to_features(board, Color.BLACK)
    assert from_black[own_check_index] == 1.0
    assert from_black[opponent_check_index] == 0.0

    from_red = board_to_features(board, Color.RED)
    assert from_red[own_check_index] == 0.0
    assert from_red[opponent_check_index] == 1.0


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


# ---------------------------------------------------------------------------
# SmallMLP -- target standardization (the actual training-divergence fix)
# ---------------------------------------------------------------------------

def test_predict_applies_y_mean_and_std():
    net = SmallMLP(input_dim=4, hidden1=3, hidden2=2, seed=5)
    net.y_mean = 500.0
    net.y_std = 200.0
    x = np.zeros((2, 4), dtype=np.float32)

    raw_standardized, _ = net.forward(x)
    real_scale = net.predict(x)

    assert np.allclose(real_scale, raw_standardized * 200.0 + 500.0)


def test_save_and_load_preserves_y_mean_and_std():
    import tempfile, os

    net = SmallMLP(input_dim=4, hidden1=3, hidden2=2, seed=6)
    net.y_mean = 123.0
    net.y_std = 456.0

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "net.npz")
        net.save(path)
        restored = SmallMLP.load(path)

    assert restored.y_mean == 123.0
    assert restored.y_std == 456.0


def test_load_defaults_y_mean_std_for_a_file_saved_without_them():
    # Backward compatibility: a network saved before this fix existed
    # (no y_mean/y_std keys at all) should load with the old no-op
    # defaults rather than raising a KeyError.
    import tempfile, os

    net = SmallMLP(input_dim=4, hidden1=3, hidden2=2, seed=7)
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "old_style_net.npz")
        np.savez(path, w1=net.w1, b1=net.b1, w2=net.w2, b2=net.b2, w3=net.w3, b3=net.b3)
        restored = SmallMLP.load(path)

    assert restored.y_mean == 0.0
    assert restored.y_std == 1.0


def test_training_on_large_scale_standardized_targets_does_not_diverge():
    # Reproduces the actual real-world failure this fix addresses:
    # Pikafish-scale labels (mean ~0, spread in the thousands of
    # centipawns) training-diverged the network to weights around
    # 1e24-1e27 before this fix. With targets properly standardized
    # (as tools/train_neural_eval.py now does), weights should stay
    # small and bounded after training, not explode.
    rng = np.random.default_rng(11)
    x = (rng.standard_normal((40, 20)) > 0).astype(np.float32)  # sparse-ish binary features
    true_weights = rng.standard_normal(20)
    y_real_scale = (x @ true_weights) * 2000  # thousands-of-centipawns-scale target

    net = SmallMLP(input_dim=20, hidden1=16, hidden2=8, seed=12)
    net.y_mean = float(y_real_scale.mean())
    net.y_std = float(y_real_scale.std())
    y_standardized = (y_real_scale - net.y_mean) / net.y_std

    for _ in range(200):
        net.train_step(x, y_standardized, lr=0.05)

    max_weight = max(np.abs(w).max() for w in (net.w1, net.b1, net.w2, net.b2, net.w3, net.b3))
    assert max_weight < 1000  # nowhere near the ~1e24 seen in the real divergence
    predictions = net.predict(x)
    assert np.all(np.isfinite(predictions))


def test_gradient_clipping_bounds_a_single_step_on_extreme_unstandardized_targets():
    # Defense-in-depth check: even WITHOUT standardization (simulating
    # someone forgetting to set y_mean/y_std, the actual mistake that
    # caused the original divergence), a single train_step with
    # max_grad_norm clipping shouldn't produce an enormous weight jump.
    rng = np.random.default_rng(13)
    x = rng.standard_normal((10, 15)).astype(np.float32)
    y_extreme = np.full(10, 9000.0)  # worst case: every label is a saturated mate score

    net = SmallMLP(input_dim=15, hidden1=8, hidden2=4, seed=14)
    net.train_step(x, y_extreme, lr=0.01, max_grad_norm=10.0)

    max_weight = max(np.abs(w).max() for w in (net.w1, net.b1, net.w2, net.b2, net.w3, net.b3))
    assert max_weight < 100  # a single clipped step should move weights only modestly
