"""V0.6.2 small MLP value network, trained by distillation from an
external, much stronger engine's evaluations (Pikafish -- see
`docs/v0.6.2.md` for the full rationale and why this project uses
distillation rather than porting Pikafish's own NNUE weights).

Pure numpy, hand-derived forward/backward pass -- no torch/sklearn
dependency, consistent with this project's practice of implementing
and understanding every piece of its own engine rather than reaching
for an off-the-shelf library (the same reasoning `engine/search.py`'s
own hand-written Negamax/Alpha-Beta/Quiescence search follows, rather
than wrapping an existing chess-search package). The network is
deliberately small (two hidden layers, `FEATURE_DIM` -> 64 -> 32 -> 1)
specifically so training is fast enough on modest, non-GPU hardware.

## A note on why backprop is tested with a numerical gradient check

Hand-derived backpropagation is exactly the kind of code where a sign
or transpose error produces something that *runs without crashing* but
trains subtly wrong (or not at all) -- the same category of bug as
`engine/mcts.py`'s value-sign convention. `tests/test_network_v062.py`
includes a direct numerical-gradient-vs-analytical-gradient check
(perturb one weight slightly, confirm the measured loss change matches
what the analytical gradient predicts) specifically because "the loss
went down during training" is much weaker evidence of correctness than
verifying the gradient computation itself against an independent method.

## Why `y_mean`/`y_std` exist, and gradient clipping in `train_step`

The first real training run (real Pikafish labels, not the fake
engine's constant test output) diverged: every weight matrix ended up
with entries around 1e24-1e27 in magnitude, and the "trained" network
predicted the exact same enormous constant regardless of input. Root
cause: Pikafish's raw `score_cp` labels range up to +/-9000 (see
`pikafish_client.py`'s `mate_score_to_cp`), and plain, un-normalized
mean-squared-error gradient descent against targets of that scale, at
a learning rate tuned assuming roughly unit-scale targets, produces
gradients large enough to blow the weights up within the first few
steps rather than converge. This is a standard, well-understood
regression-training failure mode, not a backprop-correctness bug (the
numerical gradient check above already rules that out independently).

Fixed two ways, together (defense in depth, since either alone would
likely have been enough): (1) `y_mean`/`y_std` let the network store
its own target standardization, so `predict()` always returns
real-scale centipawn values while `train_step` is fed already-
standardized (roughly unit-scale) targets by the caller (see
`tools/train_neural_eval.py`) -- this is the primary fix; (2)
`train_step` also clips the global gradient norm to `max_grad_norm`
regardless, so a future mistake (e.g. forgetting to standardize
targets again, or an unusually extreme label) degrades training
speed rather than diverging outright.
"""

import numpy as np


def _relu(x):
    return np.maximum(0, x)


def _relu_derivative(x):
    return (x > 0).astype(x.dtype)


class SmallMLP:
    """
    A tiny 2-hidden-layer MLP: input -> ReLU(hidden1) -> ReLU(hidden2)
    -> linear output (a single scalar per example, meant to regress
    toward an external engine's centipawn-style evaluation score --
    deliberately NOT squashed/bounded here, so this network's output
    is a drop-in replacement anywhere `engine/evaluation.py`'s
    `evaluate()` is called, including `engine/mcts.py`'s own `tanh`
    squashing step, which expects an unbounded raw score as input).
    """

    def __init__(self, input_dim, hidden1=64, hidden2=32, seed=None):
        rng = np.random.default_rng(seed)
        # He initialization (appropriate for ReLU hidden layers) --
        # scales initial weights by sqrt(2/fan_in) so activations
        # don't explode or vanish across layers at the start of
        # training, before any learned scaling has happened.
        self.w1 = rng.standard_normal((input_dim, hidden1)) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden1)
        self.w2 = rng.standard_normal((hidden1, hidden2)) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros(hidden2)
        self.w3 = rng.standard_normal((hidden2, 1)) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros(1)
        # Target standardization: predict() always returns values on
        # the REAL label scale (e.g. centipawns), by applying
        # `raw_output * y_std + y_mean`. Defaults (0.0, 1.0) are a
        # no-op, preserving old behavior for callers that don't set
        # these -- but training against raw, large-magnitude targets
        # without setting these first is exactly what caused this
        # class's first real-world training run to diverge (see module
        # docstring). `tools/train_neural_eval.py` sets these from the
        # training set's own mean/std before training starts.
        self.y_mean = 0.0
        self.y_std = 1.0

    def forward(self, x):
        """
        `x`: (N, input_dim) float array. Returns ((N,) predictions,
        cache) where `cache` holds the intermediate activations
        `backward` needs -- callers that only want predictions (e.g.
        at inference time) can ignore the cache. Operates entirely in
        STANDARDIZED target space (see `y_mean`/`y_std` above) -- use
        `predict()`, not `forward()`, for real-scale output.
        """
        z1 = x @ self.w1 + self.b1
        a1 = _relu(z1)
        z2 = a1 @ self.w2 + self.b2
        a2 = _relu(z2)
        y_pred = (a2 @ self.w3 + self.b3).reshape(-1)

        cache = (x, z1, a1, z2, a2)
        return y_pred, cache

    def predict(self, x):
        """
        Inference-only wrapper that returns REAL-scale predictions
        (undoing the `y_mean`/`y_std` standardization `train_step`
        trains against internally) -- this is what every caller
        outside this class should use, including `NeuralEvaluator`.
        """
        y_pred_standardized, _ = self.forward(x)
        return y_pred_standardized * self.y_std + self.y_mean

    def backward(self, cache, y_pred, y_true):
        """
        Mean-squared-error loss gradient w.r.t. every parameter, via
        manual backpropagation through the 3-layer forward pass above.
        Returns (loss, grads_dict); does NOT apply the update itself
        (see `train_step`), so this method alone is what
        `test_network_v062.py`'s numerical gradient check validates.
        """
        x, z1, a1, z2, a2 = cache
        n = x.shape[0]

        loss = np.mean((y_pred - y_true) ** 2)

        d_y_pred = (2.0 / n) * (y_pred - y_true)  # (N,)
        d_y_pred = d_y_pred.reshape(-1, 1)  # (N, 1) to match a2 @ w3 + b3 shape

        d_w3 = a2.T @ d_y_pred
        d_b3 = d_y_pred.sum(axis=0)

        d_a2 = d_y_pred @ self.w3.T
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
            "w3": d_w3, "b3": d_b3.reshape(1),
        }
        return loss, grads

    def train_step(self, x, y_true, lr, max_grad_norm=10.0):
        """
        One mini-batch gradient-descent step. `y_true` must already be
        in STANDARDIZED space (i.e. `(real_target - self.y_mean) /
        self.y_std`) -- this method has no way to know the real-scale
        target distribution itself, only the caller does (see module
        docstring and `tools/train_neural_eval.py`). Returns the
        batch's loss (in standardized-target units, not real-scale).

        `max_grad_norm`: the combined (all-parameters-concatenated)
        gradient norm is clipped to this before applying the update --
        defense-in-depth against divergence (see module docstring),
        not the primary fix, so this shouldn't normally trigger when
        targets actually are properly standardized.
        """
        y_pred, cache = self.forward(x)
        loss, grads = self.backward(cache, y_pred, y_true)

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
            y_mean=self.y_mean, y_std=self.y_std,
        )

    @classmethod
    def load(cls, path):
        data = np.load(path)
        input_dim, hidden1 = data["w1"].shape
        _, hidden2 = data["w2"].shape
        net = cls(input_dim, hidden1, hidden2)
        net.w1, net.b1 = data["w1"], data["b1"]
        net.w2, net.b2 = data["w2"], data["b2"]
        net.w3, net.b3 = data["w3"], data["b3"]
        # "y_mean"/"y_std" didn't exist before this fix -- fall back to
        # the no-op defaults (0.0, 1.0) for any network saved before
        # this change, rather than raising a KeyError on load.
        net.y_mean = float(data["y_mean"]) if "y_mean" in data else 0.0
        net.y_std = float(data["y_std"]) if "y_std" in data else 1.0
        return net
