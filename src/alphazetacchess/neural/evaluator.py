"""V0.6.2 `NeuralEvaluator`: wraps a trained `SmallMLP` so it can be
called exactly like `engine/evaluation.py`'s `evaluate(board, color)`
-- a drop-in replacement anywhere that function is currently called,
once a network has actually been trained (see `docs/v0.6.2.md` for the
full pipeline: `tools/label_positions_with_pikafish.py` ->
`tools/train_neural_eval.py` -> this class).

Wired into `SearchEngine`/`MCTSEngine` via their `eval_fn` parameter
(see `docs/v0.6.2.md`'s 5th addendum) and `tools/compare_engines.py`'s
`--use-neural-eval` flag.
"""

from .features import board_to_features, FEATURE_DIM
from .network import SmallMLP


class NeuralEvaluator:
    def __init__(self, network_path):
        self.net = SmallMLP.load(network_path)

        # neural/features.py's FEATURE_DIM changed (1260 -> 1268) when
        # auxiliary hand-crafted features were added -- a network
        # trained before that change has weight matrices sized for the
        # old, smaller input and will fail with a fairly opaque numpy
        # matmul-shape error at the first real evaluation, not at load
        # time. Check explicitly here and fail immediately with a
        # clear, actionable message instead.
        loaded_input_dim = self.net.w1.shape[0]
        if loaded_input_dim != FEATURE_DIM:
            raise ValueError(
                f"{network_path} was trained with a {loaded_input_dim}-dimensional "
                f"feature vector, but neural/features.py's current FEATURE_DIM is "
                f"{FEATURE_DIM} -- this network is from a different (likely older) "
                f"version of the feature encoding and is not compatible. Retrain with "
                f"tools/train_neural_eval.py against the current code."
            )

    def __call__(self, board, color):
        """Matches `evaluate(board, color)`'s calling convention exactly."""
        features = board_to_features(board, color)
        # SmallMLP.predict expects a batch (N, FEATURE_DIM); wrap this
        # single position as a batch of one and unwrap the result.
        score = self.net.predict(features.reshape(1, -1))[0]
        return float(score)
