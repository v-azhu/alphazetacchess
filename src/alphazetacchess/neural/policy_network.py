"""V0.9.4 small MLP policy network -- predicts a probability distribution
over `policy_encoding.POLICY_DIM` (from-square, to-square) indices,
meant to eventually replace `engine/mcts.py`'s uniform/heuristic move
priors with a trained one, the same "future policy network" V0.6.1's
own module docstring flagged `_MCTSNode.prior` as waiting for.

Deliberately a **separate** network from `network.py`'s `SmallMLP`
(the value network), not a shared trunk with two heads -- lower risk
(zero changes to `SmallMLP`'s extensively-tested existing code) for a
first checkpoint that has no real training data yet anyway (see
`docs/v0.9.4.md`); revisiting this as a shared-trunk two-head network
later, once there's an actual trained result to compare against, is a
reasonable follow-up but not attempted here.

## Why training uses ordinary (unmasked) softmax cross-entropy, and
## masking only happens at inference

A real training example is "Pikafish's actual best move was index K
in this position" -- a single target class, the same shape as any
ordinary multi-class classification problem, so ordinary softmax
cross-entropy over the full `POLICY_DIM`-way output applies directly;
illegal-move logits are never the target class, so they get pushed
down over training the same way any never-correct class does in a
normal classifier, without needing the loss itself to know which
moves are legal for which training example. Masking only matters at
**inference** time (`predict_masked_probs`), extracting a valid
probability distribution over the *actually* legal moves for whatever
specific position is being evaluated right now -- that set is
different for every position and isn't known (or needed) at training
time.

## Numerical gradient check

Same reasoning as `network.py`'s own docstring: hand-derived backprop
is exactly the kind of code that runs without crashing but computes
the wrong gradient, so `tests/test_policy_network_v094.py` verifies
`backward`'s output against a direct numerical gradient, not just
"loss went down during a training loop."
"""

import numpy as np

from .policy_encoding import POLICY_DIM


def _relu(x):
    return np.maximum(0, x)


def _relu_derivative(x):
    return (x > 0).astype(x.dtype)


class PolicyMLP:
    """A tiny 2-hidden-layer MLP: input -> ReLU(hidden1) -> ReLU(hidden2)
    -> `output_dim` raw logits (no softmax applied in `forward` --
    `backward`'s cross-entropy computes softmax internally for
    numerical stability, and `predict_masked_probs` applies a
    *masked* softmax at inference; see module docstring for why
    masking only happens there, not during training).
    """

    def __init__(self, input_dim, output_dim=POLICY_DIM, hidden1=64, hidden2=32, seed=None):
        rng = np.random.default_rng(seed)
        # He initialization, same reasoning as SmallMLP's own (ReLU
        # hidden layers): scales initial weights by sqrt(2/fan_in) so
        # activations don't explode or vanish before any learning.
        self.w1 = rng.standard_normal((input_dim, hidden1)) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden1)
        self.w2 = rng.standard_normal((hidden1, hidden2)) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros(hidden2)
        self.w3 = rng.standard_normal((hidden2, output_dim)) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros(output_dim)

    def forward(self, x):
        """`x`: (N, input_dim). Returns `((N, output_dim) raw logits,
        cache)` -- see class docstring for why these are raw logits,
        not probabilities.
        """
        z1 = x @ self.w1 + self.b1
        a1 = _relu(z1)
        z2 = a1 @ self.w2 + self.b2
        a2 = _relu(z2)
        logits = a2 @ self.w3 + self.b3

        cache = (x, z1, a1, z2, a2)
        return logits, cache

    def predict_masked_probs(self, x, legal_indices):
        """`x`: a single example, (input_dim,). `legal_indices`: the
        `policy_encoding.move_to_policy_index` values for every legal
        move in the position `x` was encoded from. Returns
        `{index: probability}` for exactly those indices, a masked
        softmax computed only over them (illegal-move logits never
        enter the computation at all, not just zeroed out afterward --
        see module docstring for why masking is an inference-time-only
        concern, not a training one).
        """
        logits, _ = self.forward(x.reshape(1, -1))
        legal_logits = logits[0, legal_indices]
        peak = legal_logits.max()
        weights = np.exp(legal_logits - peak)
        total = weights.sum()
        probs = weights / total
        return {index: float(p) for index, p in zip(legal_indices, probs)}

    def backward(self, cache, logits, y_true_indices):
        """Ordinary (unmasked) softmax cross-entropy loss and its
        gradient w.r.t. every parameter -- see module docstring for why
        training doesn't mask. `y_true_indices`: (N,) int array, the
        target class index for each example. Returns `(loss,
        grads_dict)`; does not apply the update (see `train_step`) --
        this method alone is what
        `test_policy_network_v094.py::test_backward_matches_numerical_gradient`
        validates.
        """
        x, z1, a1, z2, a2 = cache
        n = x.shape[0]

        shifted = logits - logits.max(axis=1, keepdims=True)
        exp_logits = np.exp(shifted)
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)

        correct_class_probs = probs[np.arange(n), y_true_indices]
        loss = -np.mean(np.log(correct_class_probs + 1e-12))

        d_logits = probs.copy()
        d_logits[np.arange(n), y_true_indices] -= 1
        d_logits /= n

        d_w3 = a2.T @ d_logits
        d_b3 = d_logits.sum(axis=0)

        d_a2 = d_logits @ self.w3.T
        d_z2 = d_a2 * _relu_derivative(z2)
        d_w2 = a1.T @ d_z2
        d_b2 = d_z2.sum(axis=0)

        d_a1 = d_z2 @ self.w2.T
        d_z1 = d_a1 * _relu_derivative(z1)
        d_w1 = x.T @ d_z1
        d_b1 = d_z1.sum(axis=0)

        grads = {
            "w1": d_w1, "b1": d_b1,
            "w2": d_w2, "b2": d_b2,
            "w3": d_w3, "b3": d_b3,
        }
        return loss, grads

    def train_step(self, x, y_true_indices, lr, max_grad_norm=10.0):
        """One mini-batch gradient-descent step. `max_grad_norm`: same
        defense-in-depth clipping `SmallMLP.train_step` uses, for the
        same reason (see `network.py`'s own docstring on why that
        exists) -- cross-entropy loss doesn't have `SmallMLP`'s
        raw-target-scale divergence failure mode (its own targets are
        just class indices, not unbounded centipawn-scale numbers), but
        clipping costs nothing to keep as the same safety net.
        """
        logits, cache = self.forward(x)
        loss, grads = self.backward(cache, logits, y_true_indices)

        total_norm = np.sqrt(sum(np.sum(g ** 2) for g in grads.values()))
        if total_norm > max_grad_norm:
            scale = max_grad_norm / (total_norm + 1e-8)
            grads = {name: g * scale for name, g in grads.items()}

        self.w1 -= lr * grads["w1"]
        self.b1 -= lr * grads["b1"]
        self.w2 -= lr * grads["w2"]
        self.b2 -= lr * grads["b2"]
        self.w3 -= lr * grads["w3"]
        self.b3 -= lr * grads["b3"]

        return loss

    def save(self, path):
        np.savez(
            path,
            w1=self.w1, b1=self.b1,
            w2=self.w2, b2=self.b2,
            w3=self.w3, b3=self.b3,
        )

    @classmethod
    def load(cls, path):
        data = np.load(path)
        input_dim, hidden1 = data["w1"].shape
        _, hidden2 = data["w2"].shape
        _, output_dim = data["w3"].shape
        net = cls(input_dim, output_dim, hidden1, hidden2)
        net.w1, net.b1 = data["w1"], data["b1"]
        net.w2, net.b2 = data["w2"], data["b2"]
        net.w3, net.b3 = data["w3"], data["b3"]
        return net
