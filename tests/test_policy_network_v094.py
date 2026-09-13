"""V0.9.4 tests for neural/policy_network.py's PolicyMLP."""

import numpy as np

from alphazetacchess.neural.policy_network import PolicyMLP


def test_forward_output_shape():
    net = PolicyMLP(input_dim=6, output_dim=10, hidden1=4, hidden2=3, seed=1)
    x = np.random.default_rng(0).standard_normal((5, 6))

    logits, cache = net.forward(x)

    assert logits.shape == (5, 10)


def test_backward_matches_numerical_gradient():
    # Same reasoning as network.py's own test_backward_matches_
    # numerical_gradient: hand-derived backprop is exactly the kind of
    # code that runs without error but computes the wrong gradient.
    rng = np.random.default_rng(0)
    net = PolicyMLP(input_dim=6, output_dim=5, hidden1=4, hidden2=3, seed=1)
    x = rng.standard_normal((5, 6))
    y_true_indices = rng.integers(0, 5, size=5)

    logits, cache = net.forward(x)
    _, grads = net.backward(cache, logits, y_true_indices)

    def loss_with_perturbed_w1(i, j, delta):
        original = net.w1[i, j]
        net.w1[i, j] = original + delta
        logits_perturbed, _ = net.forward(x)
        net.w1[i, j] = original
        shifted = logits_perturbed - logits_perturbed.max(axis=1, keepdims=True)
        exp_logits = np.exp(shifted)
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
        correct = probs[np.arange(5), y_true_indices]
        return -np.mean(np.log(correct + 1e-12))

    epsilon = 1e-4
    for i, j in [(0, 0), (2, 1), (5, 3)]:
        numerical_grad = (
            loss_with_perturbed_w1(i, j, epsilon) - loss_with_perturbed_w1(i, j, -epsilon)
        ) / (2 * epsilon)
        assert abs(grads["w1"][i, j] - numerical_grad) < 1e-4


def test_train_step_reduces_loss_on_a_tiny_synthetic_dataset():
    rng = np.random.default_rng(2)
    net = PolicyMLP(input_dim=8, output_dim=6, hidden1=8, hidden2=6, seed=3)
    x = rng.standard_normal((20, 8))
    y_true_indices = rng.integers(0, 6, size=20)

    logits_before, cache_before = net.forward(x)
    loss_before, _ = net.backward(cache_before, logits_before, y_true_indices)

    for _ in range(50):
        net.train_step(x, y_true_indices, lr=0.1)

    logits_after, cache_after = net.forward(x)
    loss_after, _ = net.backward(cache_after, logits_after, y_true_indices)

    assert loss_after < loss_before


def test_predict_masked_probs_is_a_valid_distribution_over_only_the_legal_indices():
    net = PolicyMLP(input_dim=6, output_dim=100, hidden1=4, hidden2=3, seed=5)
    x = np.random.default_rng(0).standard_normal(6)
    legal_indices = [3, 17, 42, 99]

    probs = net.predict_masked_probs(x, legal_indices)

    assert set(probs.keys()) == set(legal_indices)
    assert all(p > 0 for p in probs.values())
    assert abs(sum(probs.values()) - 1.0) < 1e-9


def test_predict_masked_probs_ignores_illegal_indices_entirely():
    # Not just "zeroed out after the fact" -- illegal logits must never
    # even enter the softmax normalization, or a single enormous
    # illegal-move logit could still distort the legal distribution.
    net = PolicyMLP(input_dim=4, output_dim=5, hidden1=3, hidden2=2, seed=6)
    x = np.random.default_rng(0).standard_normal(4)

    # Make one "illegal" logit artificially enormous.
    net.w3[:, 4] = 1000.0
    net.b3[4] = 1000.0

    probs_without_illegal = net.predict_masked_probs(x, [0, 1, 2])
    # Recompute with the huge logit present but not in the mask.
    probs_still_without_illegal = net.predict_masked_probs(x, [0, 1, 2])

    assert probs_without_illegal == probs_still_without_illegal
    assert abs(sum(probs_without_illegal.values()) - 1.0) < 1e-9


def test_save_and_load_round_trip_produces_identical_predictions():
    import tempfile
    import os

    rng = np.random.default_rng(3)
    net = PolicyMLP(input_dim=8, output_dim=12, hidden1=6, hidden2=4, seed=4)
    x = rng.standard_normal(8)
    legal_indices = [1, 5, 9]
    probs_before = net.predict_masked_probs(x, legal_indices)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "policy_net.npz")
        net.save(path)
        restored = PolicyMLP.load(path)

    probs_after = restored.predict_masked_probs(x, legal_indices)

    assert probs_before == probs_after
