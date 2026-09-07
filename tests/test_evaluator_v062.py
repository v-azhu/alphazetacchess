"""V0.6.2 tests for neural/evaluator.py."""

import os
import tempfile

import numpy as np
import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.neural.features import board_to_features, FEATURE_DIM
from alphazetacchess.neural.network import SmallMLP
from alphazetacchess.neural.evaluator import NeuralEvaluator


def test_neural_evaluator_matches_direct_network_prediction():
    net = SmallMLP(FEATURE_DIM, hidden1=8, hidden2=4, seed=7)
    board = Board()

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "net.npz")
        net.save(path)
        evaluator = NeuralEvaluator(path)

        score = evaluator(board, Color.RED)

    expected = net.predict(board_to_features(board, Color.RED).reshape(1, -1))[0]
    assert score == float(expected)


def test_neural_evaluator_returns_a_plain_python_float():
    net = SmallMLP(FEATURE_DIM, hidden1=4, hidden2=4, seed=8)
    board = Board()

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "net.npz")
        net.save(path)
        evaluator = NeuralEvaluator(path)
        score = evaluator(board, Color.RED)

    assert isinstance(score, float)
    assert not isinstance(score, np.floating)  # a plain float, not a numpy scalar


def test_neural_evaluator_rejects_a_network_trained_on_a_different_feature_dim():
    # Simulates loading a network saved before an auxiliary-feature
    # addition changed FEATURE_DIM -- should fail immediately and
    # clearly at construction time, not with an opaque numpy matmul
    # shape error the first time it's actually evaluated.
    stale_dim = FEATURE_DIM - 8  # pretend this was saved for the pre-auxiliary-feature encoding
    net = SmallMLP(stale_dim, hidden1=4, hidden2=4, seed=9)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "stale_net.npz")
        net.save(path)

        with pytest.raises(ValueError, match="not compatible"):
            NeuralEvaluator(path)
