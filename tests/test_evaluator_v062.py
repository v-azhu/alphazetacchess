"""V0.6.2 tests for neural/evaluator.py."""

import os
import tempfile

import numpy as np

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
