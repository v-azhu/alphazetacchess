"""V0.9.4 tests for neural/policy_evaluator.py."""

import os
import tempfile

import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.neural.features import FEATURE_DIM
from alphazetacchess.neural.policy_encoding import POLICY_DIM, move_to_policy_index
from alphazetacchess.neural.policy_network import PolicyMLP
from alphazetacchess.neural.policy_evaluator import NeuralPolicyEvaluator


def test_neural_policy_evaluator_returns_probs_for_every_legal_move():
    net = PolicyMLP(FEATURE_DIM, POLICY_DIM, hidden1=8, hidden2=4, seed=1)
    board = Board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "policy_net.npz")
        net.save(path)
        evaluator = NeuralPolicyEvaluator(path)

        priors = evaluator(board, Color.RED, legal_moves)

    assert set(priors.keys()) == set(legal_moves)
    assert all(p > 0 for p in priors.values())
    assert abs(sum(priors.values()) - 1.0) < 1e-6


def test_neural_policy_evaluator_matches_direct_masked_prediction():
    net = PolicyMLP(FEATURE_DIM, POLICY_DIM, hidden1=6, hidden2=4, seed=2)
    board = Board()
    legal_moves = Rule.generate_legal_moves(board, Color.RED)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "policy_net.npz")
        net.save(path)
        evaluator = NeuralPolicyEvaluator(path)
        priors = evaluator(board, Color.RED, legal_moves)

    from alphazetacchess.neural.features import board_to_features

    features = board_to_features(board, Color.RED)
    legal_indices = [move_to_policy_index(m, Color.RED) for m in legal_moves]
    expected = net.predict_masked_probs(features, legal_indices)

    for move in legal_moves:
        index = move_to_policy_index(move, Color.RED)
        assert priors[move] == expected[index]


def test_neural_policy_evaluator_rejects_a_network_trained_on_a_different_feature_dim():
    stale_dim = FEATURE_DIM - 8
    net = PolicyMLP(stale_dim, POLICY_DIM, hidden1=4, hidden2=4, seed=3)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "stale_net.npz")
        net.save(path)

        with pytest.raises(ValueError, match="feature encoding"):
            NeuralPolicyEvaluator(path)


def test_neural_policy_evaluator_rejects_a_network_trained_on_a_different_policy_dim():
    stale_output_dim = POLICY_DIM - 100
    net = PolicyMLP(FEATURE_DIM, stale_output_dim, hidden1=4, hidden2=4, seed=4)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "stale_net.npz")
        net.save(path)

        with pytest.raises(ValueError, match="move encoding"):
            NeuralPolicyEvaluator(path)
